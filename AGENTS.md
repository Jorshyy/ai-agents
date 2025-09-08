# Repository Guidelines

## Project Structure & Module Organization
- `taboo/game.py`: single `Game` (append-only history, `is_over()` / `finished()`, end-of-round rules).
- `taboo/player.py`: base players (`Cluer`, `Guesser`, `Buzzer`, `Judge`) with `announce(event)` and cancellable `run(coro)`.
- `taboo/agents/`: AI implementations (DSPy) and card generation.
  - `cluer.AICluer`, `guesser.AIGuesser`, `judge.AIJudge`, `card_creator.TabooCard`.
- `taboo/types.py`: Pydantic event models (discriminated by `role`, extra-forbid).
- `taboo/cli.py`: Typer CLI for running AI vs AI rounds (pretty output).
- `Makefile`: `sync`, `test`, `demo` targets.

- ## Build, Test, and Development (uv)
- Sync env: `uv sync` (uses `.python-version` and `uv.lock`).
- Run demo (agents only): `uv run python -m taboo play --target apple --guessers 3 --duration 30`.
- Run tests:
  - Ephemeral: `uvx pytest -q`.
  - Dev dep: `uv add --dev pytest` then `uv run pytest -q`.

## Demo (Typer CLI)
- Run a full agent-only round:
  - Provide a target: `uv run python -m taboo play --target apple --guessers 3 --duration 30 --name g1 --name g2 --name g3`
  - Or auto-generate a full card: `uv run python -m taboo play`
- Uses a single shared history that all players read, appending events like:
  - `{ "role": "cluer", "clue": "potato" }`
  - `{ "role": "buzzer", "clue": "potato", "allowed": true }`
  - `{ "role": "guesser", "player_id": "g1", "guess": "french fry" }`
  - `{ "role": "judge", "guess": "french fry", "is_correct": false }`
  - The CLI prefers `--target ...` and generates taboo words via DSPy. If `--target` is omitted, it generates both target and taboo words.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, PEP 8 + type hints.
- Modules/functions: `snake_case`; classes: `PascalCase`.
- Events: Pydantic models from `taboo/types.py` (discriminated by `role`).

## Testing Guidelines
- Framework: `pytest` (add as a dev dep when tests exist).
- Suggested focus: player behavior and game end conditions (buzzed/correct/timeout).
- Run: `uvx pytest -q` or `uv run pytest -q`.

## Commit & Pull Request Guidelines
- Commits: imperative, concise subjects (e.g., "Add buzzer strict gate").
- Prefer small, focused commits tied to a single concern.
- PRs: include summary, rationale, screenshots (UI), and steps to verify.
- Link related issues; note any config or migration changes.

## Security & Configuration Tips
- Keep secrets out of VCS; use a local `.env` if needed.
- Use `pyproject.toml` + `uv.lock` as the source of truth; prefer `uv add/remove` over editing `requirements.txt`.

## Logging
- The CLI sets WARNING level and pretty-prints the transcript; internal DEBUG logs remain available for debugging.
