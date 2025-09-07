from __future__ import annotations
import asyncio
import json
import os
from typing import List
import logging

from ..game import run_game
from ..player import Cluer, Buzzer, Judge, Guesser, AIClueStrategy, AIGuessStrategy


async def play_once(target: str, taboo_words: List[str], duration: int = 60, num_guessers: int = 3, pace_sec: float = 3.0) -> str:
    players = [Cluer(AIClueStrategy(pace_sec=pace_sec)), Buzzer(), Judge()] + [Guesser(player_id=f"g{i+1}", strategy=AIGuessStrategy()) for i in range(num_guessers)]
    summary = await run_game(target, taboo_words, duration_sec=duration, players=players)
    # Extract winner if present
    winner = None
    for ev in summary.get("events", []):
        if ev.role == "system" and getattr(ev, "event", None) == "end":
            winner = getattr(ev, "winner", None)
    return winner or ""


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    # Config from env for convenience
    target = os.getenv("TABOO_TARGET", "apple")
    taboo_words = json.loads(os.getenv("TABOO_WORDS", "[\"fruit\",\"red\",\"iphone\",\"mac\",\"tree\"]"))
    duration = int(os.getenv("TABOO_DURATION", "30"))
    guessers = int(os.getenv("TABOO_GUESSERS", "3"))
    pace = float(os.getenv("TABOO_CLUE_PACE", "3.0"))
    print(f"Starting serverless round (simple history): target={target}, taboo_words={taboo_words}")
    winner = asyncio.run(play_once(target, taboo_words, duration=duration, num_guessers=guessers, pace_sec=pace))
    print(f"Round finished. Winner: {winner or 'none'}")


if __name__ == "__main__":
    main()
