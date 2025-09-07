# Repository Guidelines

## Project Structure & Module Organization
- `taboo/game.py`: single `Game` (append-only history, runs players).
- `taboo/player.py`: generic players (`Cluer`, `Guesser`, `Buzzer`, `Judge`) and strategies (`AI*`, `Human*`).
- `taboo/types.py`: Pydantic event models (discriminated by `role`).
- `taboo/llm/fakellm.py`: latency-simulating model used by strategies.
- `taboo/scripts/serverless_round.py`: runs an all-agent round locally (DEBUG logs).
- `Makefile`: `sync`, `test`, `demo` targets.

## Build, Test, and Development (uv)
- Sync env: `uv sync` (uses `.python-version` and `uv.lock`).
- Run demo (agents only): `make demo`.
- Run tests:
  - Ephemeral: `uvx pytest -q`.
  - Dev dep: `uv add --dev pytest` then `uv run pytest -q`.

## Serverless Demo
- Run a full agent-only round: `make demo`.
- Uses a single shared history (`taboo/game.py`) that all agents read, appending events like:
  - `{ "role": "cluer", "clue": "potato" }`
  - `{ "role": "buzzer", "clue": "potato", "allowed": true }`
  - `{ "role": "guesser", "player_id": "g1", "guess": "french fry" }`
  - `{ "role": "judge", "guess": "french fry", "is_correct": false }`
- Env overrides: `TABOO_TARGET`, `TABOO_WORDS` (JSON list), `TABOO_DURATION`, `TABOO_GUESSERS`, `TABOO_CLUE_PACE`.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, PEP 8 + type hints.
- Modules/functions: `snake_case`; classes: `PascalCase`.
- Events: Pydantic models from `taboo/types.py` (discriminated by `role`).

## Testing Guidelines
- Framework: `pytest` (add as a dev dep when tests exist).
- Suggested focus: player strategies (logic) and game end conditions.
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
- The demo configures DEBUG logging; edit the script to change level/format.
