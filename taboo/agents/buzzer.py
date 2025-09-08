import dspy

from ..player import Buzzer


class BuzzClue(dspy.Signature):
    """
    Check if the clue is one of the taboo words (or a minor variation, like singular/plural).
    It's ok if the clue has a similar meaning to the taboo word, it just can't be the same word.
    """
    clue: str = dspy.InputField(description="The clue word or phrase given by the Cluer")
    taboo_words: list[str] = dspy.InputField(description="The taboo words that cannot be used in the clue, or you lose")

    buzz: bool = dspy.OutputField(description="Whether the clue violates the taboo words or not")
    justification: str = dspy.OutputField()


class AIBuzzer(Buzzer):
    def __init__(self, model: str = "gemini/gemini-2.5-flash-lite"):
        super().__init__()
        self.lm = dspy.LM(model=model, max_tokens=2_000, temperature=1.0)
        self.buzz_clue = dspy.Predict(BuzzClue)
        self.cache = {}

    async def _violates(self, text: str) -> str | None:
        if text in self.cache:
            return self.cache[text]
        
        with dspy.context(lm=self.lm):
            result = await self.buzz_clue.aforward(clue=text, taboo_words=self.game.taboo_words)  # type: ignore[attr-defined]

        self.cache[text] = result.justification if result.buzz else None
        return self.cache[text]