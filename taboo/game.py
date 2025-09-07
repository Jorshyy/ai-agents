from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List, cast
from collections import Counter

from .types import Event, SystemMessage
from .player import Player, Cluer, Buzzer, Guesser, Judge


log = logging.getLogger(__name__)


def validate_roles(players: List[Player]):
    counts = Counter(type(p).__name__ for p in players)
    if counts.get("Cluer", 0) != 1:
        raise ValueError("There must be exactly one Cluer.")
    if counts.get("Buzzer", 0) != 1:
        raise ValueError("There must be exactly one Buzzer.")
    if counts.get("Judge", 0) != 1:
        raise ValueError("There must be exactly one Judge.")
    if counts.get("Guesser", 0) < 1:
        raise ValueError("There must be at least one Guesser.")


class Game:
    def __init__(self, target: str, taboo_words: List[str], players: List[Player], duration_sec: int = 120):
        validate_roles(players)
        self.target = target.strip()
        self.taboo_words = [t.strip() for t in taboo_words]
        self.duration_sec = duration_sec
        self.events: list[Event] = []
        self._cond = asyncio.Condition()
        self._stop = asyncio.Event()
        self.players = players
        for p in self.players:
            p.join(self)

    async def publish(self, ev: Event):
        async with self._cond:
            self.events.append(ev)
            log.debug(f"Game.publish -> {ev}")
            self._cond.notify_all()

    def history(self) -> list[Event]:
        return list(self.events)

    async def wait_next(self, index: int) -> int:
        async with self._cond:
            await self._cond.wait_for(lambda: len(self.events) > index)
            return len(self.events)

    async def stream(self, start: int = 0):
        idx = start
        while True:
            n = await self.wait_next(idx)
            new = self.events[idx:n]
            idx = n
            for ev in new:
                yield ev

    async def play(self) -> Dict[str, Any]:
        async def timeout():
            await asyncio.sleep(self.duration_sec)
            await self.publish(SystemMessage(role="system", event="timeout"))

        async with asyncio.TaskGroup() as tg:
            for p in self.players:
                tg.create_task(p.play())
            tg.create_task(timeout())

            idx = 0
            while True:
                n = await self.wait_next(idx)
                events = self.events[idx:n]
                idx = n
                for ev in events:
                    if ev.role == "judge" and not ev.is_correct:
                        self._stop.set()
                        end_msg = SystemMessage(role="system", event="end", reason="correct")
                        if ev.by:
                            end_msg.winner = ev.by
                        await self.publish(end_msg)
                        break
                    if ev.role == "system" and ev.event == "timeout":
                        self._stop.set()
                        await self.publish(SystemMessage(role="system", event="end", reason="timeout"))
                        break
                else:
                    continue
                break

        return {"events": self.history()}


async def run_game(target: str, taboo_words: List[str], duration_sec: int, players: List[Player]) -> Dict[str, Any]:
    game = Game(target=target, taboo_words=taboo_words, players=players, duration_sec=duration_sec)
    return await game.play()
