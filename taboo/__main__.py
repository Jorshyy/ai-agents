import sys
import typer
from .cli import app, play

if __name__ == "__main__":
    # Backwards/forgiving: allow `python -m taboo play ...` or just `python -m taboo ...`
    if len(sys.argv) > 1 and sys.argv[1] == "play":
        sys.argv.pop(1)
        typer.run(play)
    else:
        app()
