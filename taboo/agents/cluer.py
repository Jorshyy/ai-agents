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

    async def next_clue(self):
        with dspy.context(lm=self.lm):
            result = await self.await_cancellable(self.generate_clue.aforward(
                target=self.game.target,  # type: ignore[attr-defined]
                taboo_words=self.game.taboo_words,  # type: ignore[attr-defined]
                history=self.game.history(),  # type: ignore[attr-defined]
                lm=self.lm))
        return result.clue
    
    async def play(self):
        while not self.game.is_over():
            try:
                clue = await self.next_clue()
            except asyncio.CancelledError:
                return
            await self.announce(ClueEvent(role="cluer", clue=clue))

    # end() is inherited from Player and will cancel/await tracked tasks
