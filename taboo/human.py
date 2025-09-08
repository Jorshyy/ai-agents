"""
Code for human players
"""
from typing import Optional
import asyncio

from .player import Cluer, Guesser, Guess


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
    
class HumanGuesser(Guesser):
    def __init__(self, player_id: str):
        super().__init__(player_id)
        self._q: asyncio.Queue[Guess] = asyncio.Queue()

    def submit(self, guess: str, rationale: Optional[str] = None):
        self._q.put_nowait(Guess(guess=guess, rationale=rationale))

    async def next_guess(self) -> Guess:
        return await self._q.get()
