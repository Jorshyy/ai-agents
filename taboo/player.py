"""
The different types of players in a Taboo game.
"""

from __future__ import annotations
import asyncio
import re
from typing import TYPE_CHECKING, Generic, TypeVar, Optional, Tuple, Any

if TYPE_CHECKING:
    from taboo.game import Game

from pydantic import BaseModel

from .types import ClueEvent, BuzzEvent, GuessEvent, JudgeEvent, SystemMessage


EventT = TypeVar('EventT', bound=ClueEvent | BuzzEvent | GuessEvent | JudgeEvent | SystemMessage)


class Player(Generic[EventT]):
    def __init__(self):
        self._game: Optional['Game'] = None
        self.id = id(self)
        self._pending: set[asyncio.Task[Any]] = set()

    async def announce(self, event: EventT):
        """Announce an event (e.g. a clue, a guess) to all the other players"""
        await self.game.publish(event)

    async def play(self):
        """Main loop of the player. Override in subclasses."""
        raise NotImplementedError

    async def end(self):
        """Cancel and await any in-flight work started via this base class."""
        if not self._pending:
            return
        # Cancel all tracked tasks
        for t in list(self._pending):
            if not t.done():
                t.cancel()
        # Await completion, suppressing cancellation
        done, pending = await asyncio.wait(self._pending, return_when=asyncio.ALL_COMPLETED)
        self._pending.clear()
        return None

    def join(self, game: 'Game') -> Player[EventT]:
        """Associate this player with a game, must be called before play()"""
        self._game = game
        return self

    # ---- Task helpers for subclasses ----
    def _track(self, task: asyncio.Task[Any]) -> asyncio.Task[Any]:
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)
        return task

    def create_task(self, coro: asyncio.coroutines.Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Create and track a cancellable task owned by this player."""
        return self._track(asyncio.create_task(coro))

    async def await_cancellable(self, coro: asyncio.coroutines.Coroutine[Any, Any, Any]) -> Any:
        """Run a coroutine as a tracked task and await its result safely."""
        task = self.create_task(coro)
        try:
            return await task
        finally:
            self._pending.discard(task)

    @property
    def game(self) -> 'Game':
        if self._game is None:
            raise RuntimeError("Player has not joined a Game. Call join(game) first.")
        return self._game



# ---- Players ----

class Cluer(Player[ClueEvent]):
    """
    Player that gives clues to help guessers guess the target word.
    """
    def __init__(self):
        super().__init__()

    async def next_clue(self) -> str:
        raise NotImplementedError

    async def play(self):
        while not self.game.is_over():
            clue = await self.next_clue()
            await self.announce(ClueEvent(role="cluer", clue=clue))

class HumanCluer(Cluer):
    """
    Human (?) cluer that can submit clues to the game via submit().
    """
    def __init__(self):
        super().__init__()
        self._q: asyncio.Queue[str] = asyncio.Queue()

    def submit(self, clue: str):
        self._q.put_nowait(clue)

    async def next_clue(self) -> str:
        return await self._q.get()

class Buzzer(Player[BuzzEvent]):
    """
    Player that buzzes if a clue violates the taboo words.
    """
    async def _violates(self, text: str) -> str | None:
        raise NotImplementedError
    
    async def play(self):
        idx = 0
        while not self.game.is_over():
            n = await self.game.wait_next(idx)
            events = self.game.events[idx:n]
            idx = n
            for ev in events:
                if ev.role == "cluer":
                    clue = ev.clue
                    reason = await self._violates(clue)
                    allowed = reason is None
                    await self.announce(BuzzEvent(role="buzzer", clue=clue, allowed=allowed, reason=reason))


class Guess(BaseModel):
    guess: str
    rationale: str | None = None

class Guesser(Player[GuessEvent]):
    """
    Player that makes guesses about the target word.
    """
    def __init__(self, player_id: str):
        super().__init__()
        self.player_id = player_id

    async def next_guess(self) -> Guess:
        raise NotImplementedError

    async def play(self):
        # Wait for the first clue to appear to avoid pre-clue spam
        if not any(e.role == "cluer" for e in self.game.events):
            async for ev in self.game.stream(start=len(self.game.events)):
                if ev.role == "cluer":
                    break
                if self.game.is_over():
                    return

        while not self.game.is_over():
            guess = await self.next_guess()
            # Skip empty guesses
            if not guess.guess or not guess.guess.strip():
                continue
            await self.announce(GuessEvent(role="guesser", player_id=self.player_id, guess=guess.guess, rationale=guess.rationale))

class HumanGuesser(Guesser):
    def __init__(self, player_id: str):
        super().__init__(player_id)
        self._q: asyncio.Queue[Guess] = asyncio.Queue()

    def submit(self, guess: str, rationale: Optional[str] = None):
        self._q.put_nowait(Guess(guess=guess, rationale=rationale))

    async def next_guess(self) -> Guess:
        return await self._q.get()

class Judge(Player[JudgeEvent]):
    """
    Player that judges whether guesses are correct.
    """
    async def check_guess(self, guess: str) -> bool:
        return guess.strip().lower() == self.game.target.lower()

    async def play(self):
        idx = 0
        while not self.game.is_over():
            n = await self.game.wait_next(idx)
            events = self.game.events[idx:n]
            idx = n
            for ev in events:
                if ev.role == "guesser":
                    is_correct = await self.check_guess(ev.guess)
                    await self.announce(JudgeEvent(role="judge", guess=ev.guess, is_correct=is_correct, by=getattr(ev, "player_id", None)))
                    if is_correct:
                        return
