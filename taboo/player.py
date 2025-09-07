from __future__ import annotations
import asyncio
import re
from typing import TYPE_CHECKING, Generic, TypeVar, Optional, Tuple

if TYPE_CHECKING:
    from taboo.game import Game

from .types import ClueEvent, BuzzEvent, GuessEvent, JudgeEvent, SystemMessage
from .llm.fakellm import FakeLLM


EventT = TypeVar('EventT', bound=ClueEvent | BuzzEvent | GuessEvent | JudgeEvent | SystemMessage)


class Player(Generic[EventT]):
    def __init__(self):
        self._game: Optional['Game'] = None
        self.id = id(self)

    async def publish(self, event: EventT):
        await self.game.publish(event)

    async def play(self):
        raise NotImplementedError

    def join(self, game: 'Game') -> Player[EventT]:
        self._game = game
        return self

    @property
    def game(self) -> 'Game':
        if self._game is None:
            raise RuntimeError("Player has not joined a Game. Call join(game) first.")
        return self._game


# ---- Strategies ----

class ClueStrategy:
    async def next_clue(self, game: 'Game') -> str:
        raise NotImplementedError


class HumanClueStrategy(ClueStrategy):
    def __init__(self):
        self._q: asyncio.Queue[str] = asyncio.Queue()

    def submit(self, clue: str):
        self._q.put_nowait(clue)

    async def next_clue(self, game: 'Game') -> str:
        return await self._q.get()


class AIClueStrategy(ClueStrategy):
    def __init__(self, pace_sec: float = 3.0):
        self.llm = FakeLLM("cluer")
        self.pace_sec = pace_sec

    async def next_clue(self, game: 'Game') -> str:
        clues_so_far = [e for e in game.history() if e.role == "cluer"]
        clue = await self.llm.clue(game.target, game.taboo_words, clues_so_far)  # type: ignore[attr-defined]
        try:
            await asyncio.wait_for(game._stop.wait(), timeout=self.pace_sec)  # type: ignore[attr-defined]
        except asyncio.TimeoutError:
            pass
        return clue


class GuessStrategy:
    async def next_guess(self, game: 'Game', player_id: str) -> Tuple[str, Optional[str]]:
        raise NotImplementedError


class HumanGuessStrategy(GuessStrategy):
    def __init__(self):
        self._q: asyncio.Queue[Tuple[str, Optional[str]]] = asyncio.Queue()

    def submit(self, guess: str, rationale: Optional[str] = None):
        self._q.put_nowait((guess, rationale))

    async def next_guess(self, game: 'Game', player_id: str) -> Tuple[str, Optional[str]]:
        return await self._q.get()


class AIGuessStrategy(GuessStrategy):
    def __init__(self):
        self.llm = FakeLLM("guesser")
        self._aiter = None

    async def next_guess(self, game: 'Game', player_id: str) -> Tuple[str, Optional[str]]:
        # Wait for at least one new event via the stream
        if self._aiter is None:
            self._aiter = game.stream(start=len(game.events))
        await self._aiter.__anext__()
        clues = [e.clue for e in game.events if e.role == "cluer"]
        approvals = {e.clue: getattr(e, "allowed", True) for e in game.events if e.role == "buzzer"}
        clues = [c for c in clues if approvals.get(c, True)]
        other_guesses = [e.guess for e in game.events if e.role == "guesser"]
        return await self.llm.guess(clues, other_guesses)


# ---- Players ----

class Cluer(Player[ClueEvent]):
    def __init__(self, strategy: ClueStrategy):
        super().__init__()
        self.strategy = strategy

    async def play(self):
        while not self.game._stop.is_set():  # type: ignore[attr-defined]
            clue = await self.strategy.next_clue(self.game)
            await self.publish(ClueEvent(role="cluer", clue=clue))


class Buzzer(Player[BuzzEvent]):
    def _violates(self, text: str) -> str | None:
        txt = text.lower()
        for w in [t.lower() for t in self.game.taboo_words]:  # type: ignore[attr-defined]
            if re.search(rf"\b{re.escape(w)}\b", txt):
                return w
        return None

    async def play(self):
        idx = 0
        while not self.game._stop.is_set():  # type: ignore[attr-defined]
            n = await self.game.wait_next(idx)
            events = self.game.events[idx:n]
            idx = n
            for ev in events:
                if ev.role == "cluer":
                    clue = ev.clue
                    reason = self._violates(clue)
                    allowed = reason is None
                    await self.publish(BuzzEvent(role="buzzer", clue=clue, allowed=allowed, reason=reason))


class Guesser(Player[GuessEvent]):
    def __init__(self, player_id: str, strategy: GuessStrategy):
        super().__init__()
        self.player_id = player_id
        self.strategy = strategy

    def _norm(self, s: str) -> str:
        return "".join(ch for ch in s.lower().strip() if ch.isalnum())

    async def play(self):
        while not self.game._stop.is_set():  # type: ignore[attr-defined]
            guess, rationale = await self.strategy.next_guess(self.game, self.player_id)
            # Deduplicate using game history for this player
            existing = {
                self._norm(e.guess) for e in self.game.events
                if e.role == "guesser" and getattr(e, "player_id", None) == self.player_id
            }
            key = self._norm(guess)
            if key in existing:
                continue
            await self.publish(GuessEvent(role="guesser", player_id=self.player_id, guess=guess, rationale=rationale))


class Judge(Player[JudgeEvent]):
    async def play(self):
        idx = 0
        while not self.game._stop.is_set():  # type: ignore[attr-defined]
            n = await self.game.wait_next(idx)
            events = self.game.events[idx:n]
            idx = n
            for ev in events:
                if ev.role == "guesser":
                    guess_val = ev.guess.strip().lower()
                    is_correct = guess_val == self.game.target.lower()  # type: ignore[attr-defined]
                    await self.publish(JudgeEvent(role="judge", guess=ev.guess, is_correct=is_correct, by=getattr(ev, "player_id", None)))
                    if is_correct:
                        return

