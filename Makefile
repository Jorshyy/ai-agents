.PHONY: test sync demo

test:
	uv run pytest -q

sync:
	uv sync

demo:
	uv run python -m taboo.scripts.serverless_round
