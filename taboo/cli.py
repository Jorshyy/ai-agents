from __future__ import annotations
import asyncio
import logging
import warnings
from typing import Optional, List

import typer

from .game import Game
from .player import Buzzer, Judge
from .agents.guesser import AIGuesser
from .agents.cluer import AICluer
from .agents.card_creator import TabooCard


app = typer.Typer(add_completion=False, no_args_is_help=True, help="Play an AI-driven Taboo demo.")


def _format_event(ev) -> str:
    r = ev.role
    if r == "cluer":
        return f"[cluer] clue: {ev.clue}"
    if r == "buzzer":
        return f"[buzzer] {'ok' if ev.allowed else 'BUZZED'}" + (f" (reason: {ev.reason})" if ev.reason else "")
    if r == "guesser":
        who = ev.player_id
        base = f"[guesser {who}] guess: {ev.guess}"
        return base + (f" — {ev.rationale}" if ev.rationale else "")
    if r == "judge":
        verdict = "CORRECT" if ev.is_correct else "no"
        by = f" by {ev.by}" if ev.by else ""
        return f"[judge]{by} -> {verdict}"
    if r == "system":
        if ev.event == "timeout":
            return "[system] timeout"
        if ev.event == "end":
            reason = ev.reason or "unknown"
            win = ev.winner
            return f"[system] end: {reason}" + (f", winner: {win}" if win else "")
    return f"[{r}] {ev}"


@app.command()
def play(
    target: Optional[str] = typer.Option(None, help="Target word. If omitted, a full card is auto-generated."),
    guessers: int = typer.Option(3, min=1, help="Number of AI guessers"),
    duration: int = typer.Option(60, min=5, help="Round duration in seconds"),
    model: Optional[str] = typer.Option(None, help="LLM model name for DSPy agents"),
    names: Optional[List[str]] = typer.Option(None, "--name", help="Optional guesser names (repeat for multiple). Defaults to g1..gN."),
):
    """Run an AI vs AI Taboo round and print the transcript."""
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    # Suppress noisy asyncio warnings about cancelled, un-awaited LLM internals
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        module=r"asyncio\.base_events",
        message=r"coroutine '.*' was never awaited",
    )

    # Build the game card
    if target:
        card = TabooCard.from_target(target)
    else:
        card = TabooCard.generate()

    typer.echo(f"Card: target={card.target}, taboo_words={card.taboo_words}")

    # Build players
    m = model or "gemini/gemini-2.5-flash"
    if names and len(names) != guessers:
        raise typer.BadParameter(f"Number of --name values ({len(names)}) must match --guessers ({guessers}).")
    ids = names or [f"g{i+1}" for i in range(guessers)]
    players = [AICluer(model=m), Buzzer(), Judge()] + [AIGuesser(player_id=pid, model=m) for pid in ids]
    game = Game(target=card.target, taboo_words=card.taboo_words, players=players, duration_sec=duration)

    async def _run():
        async def render_stream() -> str:
            winner: str | None = None
            async for ev in game.stream():
                print(_format_event(ev))
                if ev.role == "system" and ev.event == "end":
                    winner = ev.winner
                    break
            return winner or ""

        render_task = asyncio.create_task(render_stream())
        await game.play()
        w = await render_task
        typer.echo(f"\nRound finished. Winner: {w or 'none'}")

    asyncio.run(_run())
