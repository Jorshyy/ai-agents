.PHONY: test sync demo

test:
	uv run pytest -q

sync:
	uv sync

demo:
	uv run python -m taboo play --target apple --guessers 3 --duration 30
