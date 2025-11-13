from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, List

from .types import Event, SystemMessage
from .player import Player, Cluer, Buzzer, Guesser, Judge


log = logging.getLogger(__name__)


def validate_roles(players: List[Player]):
    n_cluer = sum(1 for p in players if isinstance(p, Cluer))
    n_buzzer = sum(1 for p in players if isinstance(p, Buzzer))
    n_judge = sum(1 for p in players if isinstance(p, Judge))
    n_guesser = sum(1 for p in players if isinstance(p, Guesser))
    if n_cluer != 1:
        raise ValueError("There must be exactly one Cluer.")
    if n_buzzer != 1:
        raise ValueError("There must be exactly one Buzzer.")
    if n_judge != 1:
        raise ValueError("There must be exactly one Judge.")
    if n_guesser < 1:
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

    # Public termination helpers
    def is_over(self) -> bool:
        return self._stop.is_set()

    # Await until the game is finished.
    async def finished(self) -> None:
        await self._stop.wait()

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

        # Launch players and timeout tasks
        player_tasks: list[asyncio.Task] = [asyncio.create_task(p.play()) for p in self.players]
        timeout_task = asyncio.create_task(timeout())

        try:
            idx = 0
            while True:
                n = await self.wait_next(idx)
                events = self.events[idx:n]
                idx = n
                for ev in events:
                    if ev.role == "buzzer" and ev.violates_taboo:
                        self._stop.set()
                        await self.publish(SystemMessage(role="system", event="end", reason="buzzed"))
                        raise asyncio.CancelledError()
                    if ev.role == "judge" and ev.is_correct:
                        self._stop.set()
                        end_msg = SystemMessage(role="system", event="end", reason="correct")
                        if ev.by:
                            end_msg.winner = ev.by
                        await self.publish(end_msg)
                        raise asyncio.CancelledError()
                    if ev.role == "system" and ev.event == "timeout":
                        self._stop.set()
                        await self.publish(SystemMessage(role="system", event="end", reason="timeout"))
                        raise asyncio.CancelledError()
        except asyncio.CancelledError:
            # Signal players to end in-flight work quickly
            await asyncio.gather(*(p.end() for p in self.players), return_exceptions=True)
            # Cancel tasks to unblock any waits
            for t in player_tasks:
                t.cancel()
            timeout_task.cancel()
            await asyncio.gather(*player_tasks, return_exceptions=True)
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass

        return {"events": self.history()}


async def run_game(target: str, taboo_words: List[str], duration_sec: int, players: List[Player]) -> Dict[str, Any]:
    game = Game(target=target, taboo_words=taboo_words, players=players, duration_sec=duration_sec)
    return await game.play()
