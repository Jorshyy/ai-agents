# PRD: Async, Agent-Based **Taboo** Game (DSPy-friendly)

## 0) Summary / Goal

Build a real-time, event-driven Taboo game where:

* A **Cluer** (LLM or human) gives clues about a secret target word.
* **Guessers** (N ≥ 1; LLM and/or human) make guesses concurrently and speculatively as new info arrives.
* A **Buzzer** flags taboo violations.
* A **Judge** validates guesses (exact/fuzzy).
* **GameHub** coordinates rounds, timing, scores, and cancellation.

Hard requirement: **“say results as they finish.”** As soon as any agent completes a task (clue, guess, buzz, judgement), it is broadcast and rendered.

The orchestration must be **async** and **decoupled** (pub/sub). Agents are independently testable and composable. DSPy can be used inside agent implementations, but orchestration is framework-agnostic.

---

## 1) Success Criteria / Acceptance Tests

* **AC1 (concurrency):** With ≥3 LLM guessers, clues streaming every \~3s, and humans connected, guesses appear in the transcript in completion order (not issuance order).
* **AC2 (cancellation):** When a correct guess arrives, the round **immediately ends**; all pending LLM calls are cancelled; no additional clues/guesses render.
* **AC3 (buzzer modes):** Support both

  * **Classic**: clue broadcasts; buzzer can buzz post-hoc (penalty).
  * **Strict-gate**: buzzer must approve before clue is broadcast.
* **AC4 (rate limiting):** Global semaphore enforces a max of K concurrent LLM calls across all agents; no 429s in soak tests.
* **AC5 (humans):** Humans can join as cluer and/or guesser via WebSocket UI; their messages appear as events and are judged/buzzed same as LLM events.
* **AC6 (reliability):** If an agent or UI client disconnects, the round continues; reconnect restores stream state.
* **AC7 (observability):** Structured event log (JSON) with round\_id, agent\_id, latency, and token counts (if available). A `/health` endpoint returns OK; a `/metrics` endpoint exposes counters/histograms.
* **AC8 (tests):** Deterministic FakeLLM load test demonstrates “as-completed” ordering and cancellation with reproducible seeds.

---

## 2) Users & Roles

* **Player (Human Guesser)**: sends guesses, sees clues, sees other guesses, sees buzzes/judgements.
* **Cluer (Human or LLM)**: sends clues; receives taboo feedback (buzzes), sees guesses.
* **Host** (optional UI persona): starts/stops rounds, sets rules/timers, selects target/taboo list.
* **Agents (LLM)**: cluer, N guessers, buzzer, judge—each isolated and replaceable.

---

## 3) Game Rules (Configurable)

* **Target word**: string.
* **Taboo words**: list\[str].
* **Round duration**: default 90s.
* **Buzzer mode**: `"classic"` or `"strict"`.
* **Guess limit per agent** (optional): default unlimited.
* **Penalty on buzz** (classic): +1 strike to cluer; 3 strikes auto-end round (configurable).
* **Judging**:

  * **Exact** first (case/whitespace-insensitive).
  * Optional **fuzzy** (Levenshtein ≤ 1–2) before **LLM judge** (for synonyms).
  * Configurable tolerance chain.

---

## 4) System Architecture

### 4.1 Components

* **Event Bus (in-process)**: tiny pub/sub built on `asyncio.Queue` (one queue per subscriber for broadcast).
* **GameHub**: the round controller (timers, scoring, termination, lifecycle, persistence hooks).
* **Agents**:

  * **Cluer** (LLM & Human variants)
  * **Guessers** (M ≥ 1; LLM & Human variants; each can have a persona)
  * **Buzzer** (rules-based; optional LLM escalation)
  * **Judge** (exact→fuzzy→LLM hybrid)
* **RateLimiter**: global `asyncio.Semaphore(K)` around all model calls.
* **Web API**: REST for setup; WebSocket for real-time event stream & input.
* **Store**: ephemeral in-memory state per round; optional SQLite for matches/scores.

### 4.2 Concurrency Model

* **One `asyncio.TaskGroup` per round**. On correct or timeout → cancel group → immediate teardown.
* Agents subscribe to event topics; **spawn speculative tasks** on every new clue/guess.
* Use `asyncio.as_completed` (or per-task callbacks) to emit results **as they finish**.
* **Backpressure policy**: queue `maxsize` + publisher timeout → drop or warn slow subscribers (configurable).

---

## 5) Event Model (Topics & Schemas)

### 5.1 Topics

* `clue.proposed`
* `clue.approved`
* `buzzed`
* `guess.said`
* `judgement`
* `round.started`, `round.timeout`, `round.ended`
* `system.error`
* `*` (catch-all for logging)

### 5.2 Event Base

```python
# Python type sketch (Pydantic recommended)
class Event(BaseModel):
    id: str
    ts: float
    round_id: str
    type: str
    by: str  # agent_id or "human:{socket_id}"
```

### 5.3 Event Payloads

```python
class ClueProposed(Event):
    type: Literal["clue.proposed"] = "clue.proposed"
    text: str

class ClueApproved(Event):
    type: Literal["clue.approved"] = "clue.approved"
    text: str

class Buzzed(Event):
    type: Literal["buzzed"] = "buzzed"
    reason: str  # taboo word or rule id
    offending_text: str

class GuessSaid(Event):
    type: Literal["guess.said"] = "guess.said"
    guess: str
    rationale: Optional[str] = None

class Judgement(Event):
    type: Literal["judgement"] = "judgement"
    guess_by: str
    guess: str
    verdict: Literal["correct","incorrect","close"]
    explanation: Optional[str] = None

class RoundStarted(Event):
    type: Literal["round.started"] = "round.started"
    config: dict  # target redacted from clients unless cluer=LLM

class RoundEnded(Event):
    type: Literal["round.ended"] = "round.ended"
    reason: Literal["correct","timeout","strikes","abort"]
    winner: Optional[str] = None
```

---

## 6) API & Protocol

### 6.1 REST (setup / admin)

* `POST /rounds`

  * Body: `{ "buzzer_mode": "classic|strict", "duration_sec": 90, "target": "apple", "taboo": ["fruit","red","iphone","mac","tree"] }`
  * Returns: `{ "round_id": "r-123" }`
* `POST /rounds/{id}/start`
* `POST /rounds/{id}/abort`
* `GET  /rounds/{id}/state` (debug; redacts target for guessers)
* `GET  /health`
* `GET  /metrics` (Prometheus exposition)

### 6.2 WebSocket (bi-directional events)

* `GET /ws?role=guesser|cluer|spectator&name=Joel`
* Server pushes **all** public events for the round the client joined.
* Client may send:

  * `{ "type": "guess.said", "guess": "..." }`
  * `{ "type": "clue.proposed", "text": "..." }` (if role=cluer)
  * `{ "type": "control.join_round", "round_id": "r-123" }`

**Auth**: for MVP, anonymous name; add JWT later if needed.

---

## 7) Agent Contracts

### 7.1 Cluer (LLM)

* **Inputs**: target, taboo list, event snapshots (recent `guess.said`, prior clues, buzzes), persona.
* **Behavior**:

  * Generate one clue every `T` seconds (configurable), **or** after new info arrives.
  * On `strict` mode: publish `clue.proposed` only; wait for buzzer to re-emit `clue.approved`.
  * On `classic` mode: publish `clue.proposed`; buzzer may buzz post-hoc; Hub increments strikes.
* **Rate-limit**: acquire global semaphore before LLM call; timeout with jittered retry.

### 7.2 Guesser (LLM)

* **Inputs**: stream of `clue.approved` and `guess.said` (others); persona; local dedupe set.
* **Behavior**:

  * Spawn a new guess task on any new signal (new clue or new guess), even if previous guess is running.
  * Maintain `max_concurrent` tasks per agent; cancel stale tasks on round end.
  * Emit `guess.said` with optional rationale.
* **Dedupe**: do not repeat normalized guesses (lower, strip punctuation).

### 7.3 Buzzer

* **Inputs**: taboo list; `clue.proposed` events.
* **Behavior**:

  * Check violations using **word-boundary** matching (v1) and lowercase; configurable synonyms later.
  * `strict`: only re-emit `clue.approved` if no violation; else emit `buzzed`.
  * `classic`: always re-emit `clue.approved`; also emit `buzzed` if violated.
* **Extensibility**: optional LLM secondary check for near-misses (“sounds like”, lemmatization).

### 7.4 Judge

* **Inputs**: target, `guess.said`.
* **Behavior (chain)**:

  1. **Exact** normalized equality → correct.
  2. Optional **fuzzy** (edit distance ≤ N).
  3. Optional **LLM** synonym check (prompt with target, guess).
* **On correct**: emit `judgement(correct)` and **end round**.

---

## 8) State & Persistence

### 8.1 In-Memory per Round

```python
class RoundState(BaseModel):
    round_id: str
    config: RoundConfig
    started_at: float
    strikes: int = 0
    clues: list[str] = []
    guesses: list[tuple[str,str]] = []  # (by, guess)
    winner: Optional[str] = None
    ended_reason: Optional[str] = None
```

### 8.2 Optional SQLite (v1.1)

* Tables: `matches(id, created_at)`, `rounds(id, match_id, config_json, winner, reason, duration)`, `events(id, round_id, ts, type, payload_json)`, `scores(player, points)`.

---

## 9) Configuration & Env

* `TABOO_MODE` = `classic|strict`
* `ROUND_DURATION_SEC` (default 90)
* `GLOBAL_MAX_CONCURRENCY` (e.g., 6)
* `MODEL_NAME` / provider keys
* `LOG_LEVEL`, `LOG_REDACT` (scrub model outputs if needed)
* `PORT` (HTTP/WS)

---

## 10) Observability

* **Structured JSON logs** for every event published (include latencies for LLM calls).
* **Counters**: events by type, guesses per agent, buzz count, time-to-first-guess, time-to-correct.
* **Histograms**: LLM latency, token usage (if available), queue depth.
* **/metrics**: Prometheus exposition.
* **Trace IDs**: include `round_id` in every span; add `agent_task_id` for LLM calls.

---

## 11) Error Handling & Backpressure

* **Queue policy**: each subscriber queue `maxsize=100`. On `publish`, use `asyncio.wait_for(q.put(ev), timeout=0.1)`:

  * If timeout → log `slow_subscriber` warning and **drop** for that subscriber (do not block system).
* **LLM failures**: retry with exponential backoff and jitter up to 2 attempts; then emit `system.error`.
* **Cancellation**: on round end, cancel the `TaskGroup`; agents must catch `CancelledError` and exit quickly.

---

## 12) Security & Privacy

* Do not broadcast the **target** to guessers/spectators. Only to cluer LLM and host.
* Redact provider keys; never log full prompts/responses unless `LOG_REDACT=false` in dev.
* WebSocket origin checks; basic rate limiting on inbound messages (e.g., 10/sec).

---

## 13) UI (MVP)

* **Single-page Web UI** (or TUI first if easier):

  * Chat transcript area rendering the event stream (role-colored lines).
  * Input box for clue (if role=cluer) or guess (if role=guesser).
  * HUD: timer countdown, strikes, buzzer mode, participants.
  * Join flow: choose name & role, then join a round.
* **Latency target**: UI shows an event < 100ms from server publish on localhost.

---

## 14) Implementation Plan

### 14.1 Project Layout

```
taboo/
  app.py                 # FastAPI/Starlette + WebSocket
  bus.py                 # in-process event bus
  hub.py                 # GameHub (round lifecycle)
  agents/
    cluer_llm.py
    cluer_human.py
    guesser_llm.py
    guesser_human.py
    buzzer.py
    judge.py
  llm/
    dspy_cluer.py
    dspy_guesser.py
    dspy_judge.py
    fakellm.py
  models.py              # pydantic event/state
  config.py
  store.py               # (optional) sqlite persistence
  ui/                    # web assets or TUI
  tests/
    test_concurrency.py
    test_cancellation.py
    test_buzzer_modes.py
    test_judge_chain.py
```

### 14.2 Event Bus (spec)

* `subscribe(topic: str) -> asyncio.Queue`
* `emit(event: Event) -> None`  (internally publishes to `event.type` and `"*"`)

### 14.3 GameHub (spec)

* `run_round(round_id, agents, config) -> None`

  * Creates TaskGroup; spawns agents; listens for `judgement(correct)` and `round.timeout`; emits `round.ended` and cancels group.
* `_round_clock(duration)`; `_handle_buzz` (strikes and penalties in classic).

### 14.4 Global RateLimiter (spec)

* `with await limiter.token(): await model.call(...)`
* Uses `asyncio.Semaphore(K)`; optional tenant-aware partitioning later.

### 14.5 DSPy Modules (interface)

* `CluerLLM.clue_acall(history, persona) -> str`
* `GuesserLLM.guess_acall(snapshot, persona) -> tuple[str, Optional[str]]`
* `JudgeLLM.judge_acall(target, guess) -> verdict, explanation` (optional if fuzzy fails)

---

## 15) Test Plan

### 15.1 Unit

* **Bus**: broadcast to 3 subs; ensure per-subscriber ordering; drop on slow sub.
* **Buzzer**: boundary-aware taboo detection.
* **Judge**: exact/fuzzy chain; casing/whitespace.
* **RateLimiter**: concurrency cap with 20 simultaneous fake calls.

### 15.2 Integration (FakeLLM)

* Seeded FakeLLM that:

  * Sleeps random(0.1–1.0)s,
  * Returns a predefined sequence of clues/guesses,
  * Optionally produces taboo violations.
* Validate:

  * Results appear in **completion order**,
  * Cancellation on correct guess,
  * Round timeout ends tasks.

### 15.3 Soak

* 5 rounds × 5 guessers × 1 cluer on loop for 10 minutes, no memory growth, stable metrics.

---

## 16) Non-Functional Requirements

* **Performance**: With 1 cluer + 5 guessers + strict gate, steady CPU < 50% on dev laptop; p95 end-to-end event latency < 200ms (no external LLM).
* **Scalability**: Single process MVP; future: Redis pub/sub to scale multi-process.
* **Portability**: Python 3.11+; no OS-specific features.
* **Config via env**; 12-factor friendly.

---

## 17) Risks & Mitigations

* **LLM latency variance** → bursty completions.
  *Mitigation*: speculative guesses + as-completed rendering; cancellation on end.
* **Backpressure from slow UIs** → stalled bus.
  *Mitigation*: bounded queues + publish timeouts + drop policy.
* **Synonym judging ambiguity**.
  *Mitigation*: exact→fuzzy→LLM chain; log contested cases.
* **Prompt injection / taboo evasion** (LLM cluer).
  *Mitigation*: reinforce taboo system prompt; run buzzer as rule-checker post-hoc too.

---

## 18) V0 Scope (2–4 days of coding)

* In-process bus, GameHub, strict + classic modes.
* LLM-free FakeLLM agents to validate orchestration.
* Minimal WebSocket UI (one page) for human cluer/guesser.
* Exact judge, boundary-based buzzer.
* Global concurrency guard; basic metrics & logs.

## 19) V1 Enhancements

* DSPy-powered cluer/guessers with personas.
* Fuzzy judge (edit distance) + optional LLM judge.
* SQLite persistence for matches; scoreboard.
* Synonym taboo expansion (lemmatizer/word2vec/LLM).
* Multi-round matches & team scoring.

---

## 20) Developer Notes / Code Specs

### 20.1 Bus (reference interface)

```python
class Bus:
    def subscribe(self, topic: str) -> asyncio.Queue: ...
    async def publish(self, topic: str, event: Event) -> None: ...
    async def emit(self, event: Event) -> None: ...  # publishes to event.type and "*"
```

### 20.2 As-Completed Emission (pattern)

```python
tasks = [asyncio.create_task(call_ai(x)) for x in batch]
for fut in asyncio.as_completed(tasks):
    result = await fut
    await bus.emit(result_event(result))
```

### 20.3 Cancellation

* Wrap long-running loops in `asyncio.TaskGroup()`.
* On `round.ended` or `judgement(correct)`, **raise** inside Hub to unwind the TaskGroup.
* Agents catch `asyncio.CancelledError` and `return` quickly; don’t swallow.

### 20.4 Dedupe

* Maintain `seen: set[str]` of normalized guesses per agent; drop repeats silently.

---

## 21) Example Prompts (DSPy Signatures)

**Cluer**

* System: “You are a Taboo cluer. Target: `{target}`. Never use taboo words: `{taboo}`. Style: `{persona}`. Consider prior guesses: `{history}`. Produce a single short clue, no target, no taboo.”
* Output: `clue: str`

**Guesser**

* System: “You are a Taboo guesser (`{persona}`). Given clues: `{clues}` and others’ guesses: `{other_guesses}`, produce your **best single guess** and a one-sentence rationale.”
* Output: `guess: str`, `rationale: str`

**Judge (LLM fallback)**

* System: “Are `{guess}` and target `{target}` the same answer for Taboo? Consider synonyms and pluralization. Return verdict=correct/incorrect/close and one-sentence explanation.”

---

That’s the full, coder-ready plan. If you want, I can spin a minimal repo skeleton (FastAPI + websockets + FakeLLM + TaskGroup round runner) that implements V0 exactly as specified.
