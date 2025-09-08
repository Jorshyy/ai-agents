import dspy

from ..player import Buzzer


class BuzzClue(dspy.Signature):
    clue: str = dspy.InputField(description="The clue word or phrase given by the Cluer")
    taboo_words: list[str] = dspy.InputField(description="The taboo words that cannot be used in the clue, or you lose")

    violates: str | None = dspy.OutputField(description="If the clue violates any taboo words, return the first violating word; otherwise don't return anything")


class AIBuzzer(Buzzer):
    def __init__(self, model: str = "gemini/gemini-2.5-flash-lite"):
        super().__init__()
        self.lm = dspy.LM(model=model, max_tokens=2_000, temperature=1.0)
        self.buzz_clue = dspy.Predict(BuzzClue)

    async def _violates(self, text: str) -> str | None:
        with dspy.context(lm=self.lm):
            result = await self.buzz_clue.aforward(clue=text, taboo_words=self.game.taboo_words)  # type: ignore[attr-defined]
        return result.violates  