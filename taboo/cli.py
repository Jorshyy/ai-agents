from __future__ import annotations
import asyncio
import logging
import warnings
from typing import Optional
import itertools
import random

import typer


from .agents import AIBuzzer, AICluer, AIJudge, AIGuesser
from .agents.card_creator import TabooCard
from .game import Game
from .types import Event

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Play an AI-driven Taboo demo.")

PERSONALITIES = ['friendly', 'sarcastic', 'enthusiastic', 'thoughtful', 'mischievous']
random.shuffle(PERSONALITIES)
personalities = itertools.cycle(PERSONALITIES)


def _format_event(ev: Event) -> str:
    r = ev.role
    if r == "cluer":
        return f"[cluer] {ev.clue}"
    if r == "buzzer":
        return f"[buzzer] {'ok' if ev.allowed else 'BUZZED'}" + (f" (reason: {ev.reason})" if ev.reason else "")
    if r == "guesser":
        who = ev.player_id
        base = f"[guesser {who}] {ev.guess}"
        return base + (f" — {ev.rationale}" if ev.rationale else "")
    if r == "judge":
        verdict = "CORRECT" if ev.is_correct else "INCORRECT"
        by = f" {ev.guess} by {ev.by}"
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

    players = [
        AICluer(), 
        AIBuzzer(), 
        AIJudge()
    ]
    
    for i in range(guessers):
        personality = next(personalities)
        pid = f"p{i+1}-{personality}"
        players.append(AIGuesser(player_id=pid, personality=personality))

    game = Game(target=card.target, taboo_words=card.taboo_words, players=players, duration_sec=duration)

    async def _run():
        async def render_stream() -> str:
            winner: str | None = None
            async for ev in game.stream():
                print(_format_event(ev))
                print()
                if ev.role == "system" and ev.event == "end":
                    winner = ev.winner
                    break
            return winner or ""

        render_task = asyncio.create_task(render_stream())
        await game.play()
        w = await render_task
        typer.echo(f"\nRound finished. Winner: {w or 'none'}")

    asyncio.run(_run())
