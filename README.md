# Simple Taboo (Single‑History Agents)

This repository implements a minimal Taboo-style game using a single shared, append-only history. All agents (cluer, buzzer, guessers, judge) listen to that one history and append their own events. This mirrors a real table‑top game and keeps the system easy to reason about.

Key ideas
- One append‑only history; no topics, no server.
- Players (cluer, buzzer, guessers, judge) operate concurrently.
- Pydantic events with a `role` discriminator enforce shape.

Quickstart (uv)

```bash
# install project deps (uses .python-version and uv.lock)
uv sync

# run a full AI vs AI round (Typer CLI)
uv run python -m taboo play --target apple --guessers 3 --duration 30 --name joel --name gpt5 --name mocha

# or let DSPy generate taboo words for a provided target
uv run python -m taboo play --target apple

# or auto‑generate an entire card (target + taboo words)
uv run python -m taboo play
```

How it works
- `taboo/game.py` defines `Game` (append‑only history) and coordinates players; end rules:
  - `judge.is_correct = true` ends with reason `correct` and winner set.
  - A disallowed clue (`buzzer.allowed = false`) ends with reason `buzzed` (cluer loses).
  - Timeout ends with reason `timeout`.
- `taboo/player.py` defines generic players `Cluer`, `Guesser`, `Buzzer`, `Judge` with:
  - `announce(event)` to emit events, `run(coro)` for cancellable work, `is_over()` for loop checks.
- `taboo/agents/` contains AI implementations (DSPy):
  - `cluer.AICluer`, `guesser.AIGuesser`, `judge.AIJudge`, plus `card_creator.TabooCard`.
- `taboo/types.py` defines Pydantic event models (discriminated by `role`):
  - `{ "role": "cluer", "clue": "..." }`
  - `{ "role": "buzzer", "clue": "...", "allowed": true|false }`
  - `{ "role": "guesser", "player_id": "g1", "guess": "..." }`
  - `{ "role": "judge", "guess": "...", "is_correct": true|false }`
- The CLI constructs AI players, runs a round locally until correct/timeout, and prints a readable transcript. If `--target` is omitted, it auto‑generates a game card via DSPy (`taboo/agents/card_creator.py`).
