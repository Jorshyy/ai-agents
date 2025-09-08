import dspy
import asyncio

from ..player import Cluer
from ..types import ClueEvent, Event


class GenerateClue(dspy.Signature):
    target: str = dspy.InputField(description="The target word we want the players to guess")
    taboo_words: list[str] = dspy.InputField(description="The taboo words that cannot be used in the clue, or you lose")
    history: list[Event] = dspy.InputField(description="The history of the game so far, including previous clues, buzzes, guesses, and judgments")

    clue: str = dspy.OutputField(description="A single word or short phrase that is a clue to the target word, without using any of the taboo words")


class AICluer(Cluer):
    def __init__(self, model: str = "gemini/gemini-2.5-flash"):
        super().__init__()
        self.lm = dspy.LM(model=model, max_tokens=20_000, temperature=1.0)
        self.generate_clue = dspy.Predict(GenerateClue)
        self._pending: asyncio.Task | None = None

    async def next_clue(self):
        with dspy.context(lm=self.lm):
            task = asyncio.create_task(self.generate_clue.aforward(
                target=self.game.target,  # type: ignore[attr-defined]
                taboo_words=self.game.taboo_words,  # type: ignore[attr-defined]
                history=self.game.history(),  # type: ignore[attr-defined]
                lm=self.lm))
            self._pending = task
            try:
                result = await task
            finally:
                self._pending = None
        return result.clue
    
    async def play(self):
        while not self.game._stop.is_set():  # type: ignore[attr-defined]
            try:
                clue = await self.next_clue()
            except asyncio.CancelledError:
                return
            await self.announce(ClueEvent(role="cluer", clue=clue))

    async def end(self):
        if self._pending and not self._pending.done():
            self._pending.cancel()
            try:
                await self._pending
            except asyncio.CancelledError:
                pass
