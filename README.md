# Simple Taboo (Single-History Agents)

This repository implements a minimal Taboo-style game using a single shared, append-only history. All agents (cluer, buzzer, guessers, judge) listen to that one history and append their own events. This mirrors a real table‑top game and keeps the system easy to reason about.

Key ideas
- One history list. No pub/sub topics or server required.
- Agents operate concurrently via asyncio and decide which events to react to.
- A small fake LLM (`taboo/llm/fakellm.py`) simulates thinking and latency.

Quickstart (uv)

```bash
# install project deps (uses .python-version and uv.lock)
uv sync

# run a full agent-only round
make demo

# optional: tune via env vars
TABOO_TARGET=apple TABOO_WORDS='["fruit","red","iphone","mac","tree"]' TABOO_DURATION=30 TABOO_GUESSERS=3 make demo
```

How it works
- `taboo/game.py` defines `Game` (single object with an append‑only history) and runs injected players.
- `taboo/player.py` defines generic players `Cluer`, `Guesser`, `Buzzer`, `Judge` and pluggable strategies:
  - Clue: `AIClueStrategy(pace_sec)` or `HumanClueStrategy().submit("...")`
  - Guess: `AIGuessStrategy()` or `HumanGuessStrategy().submit("...", rationale)`
- `taboo/types.py` defines Pydantic event models (discriminated by `role`):
  - `{ "role": "cluer", "clue": "..." }`
  - `{ "role": "buzzer", "clue": "...", "allowed": true|false }`
  - `{ "role": "guesser", "player_id": "g1", "guess": "..." }`
  - `{ "role": "judge", "guess": "...", "is_correct": true|false }`
- `taboo/scripts/serverless_round.py` constructs AI players, runs a round locally until correct/timeout, and configures DEBUG logging.

Next steps
- Swap `FakeLLM` with real models (DSPy or API-backed) behind the same interface.
- Add richer judging (fuzzy match or LLM) and smarter clueing.
