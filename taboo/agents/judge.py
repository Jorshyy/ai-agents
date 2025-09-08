import dspy

from ..player import Judge


class CheckGuess(dspy.Signature):
    """
    Check if the guess matches the target word.
    Minor variations like singular/plural or -ing are acceptable.
    """
    target: str = dspy.InputField(description="The target word we want the players to guess")
    guess: str = dspy.InputField(description="The guessed word")

    is_correct: bool = dspy.OutputField(description="Whether the guess is correct or not")
    justification: str = dspy.OutputField(description="A brief explanation of why the guess is correct or not")

class AIJudge(Judge):
    def __init__(self, model: str = "gemini/gemini-2.5-flash-lite"):
        super().__init__()
        self.lm = dspy.LM(model=model, max_tokens=2_000, temperature=1.0)
        self.checker = dspy.Predict(CheckGuess)
        self.cache = {}

    async def check_guess(self, guess: str) -> bool:
        if guess in self.cache:
            return self.cache[guess]

        with dspy.context(lm=self.lm):
            result = await self.checker.aforward(
                target=self.game.target,  # type: ignore[attr-defined]
                guess=guess
            )
            self.cache[guess] = result.is_correct

        return self.cache[guess]
