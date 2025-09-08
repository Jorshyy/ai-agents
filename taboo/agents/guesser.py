import dspy

from ..player import Guesser, Guess


class GuessWord(dspy.Signature):
    """
    You are playing a game of Taboo. Your goal is to guess the target word based on the clues given by the Cluer.
    """

    history: list = dspy.InputField(description="The history of the game so far, including previous clues, buzzes, guesses, and judgments")
    player_id: str = dspy.InputField(description="The ID of the player making the guess")
    player_personality: str | None = dspy.InputField(description="Optional personality or background information about the player making the guess")

    guess: str = dspy.OutputField(description="The guessed word")
    rationale: str | None = dspy.OutputField(description="Optional rationale for the guess")


class AIGuesser(Guesser):
    def __init__(self, player_id: str, personality: str | None = None, model: str = "gemini/gemini-2.5-flash"):
        super().__init__(player_id)
        self.player_personality = personality
        self.lm = dspy.LM(model=model, max_tokens=20_000, temperature=1.0)
        self.guess_fn = dspy.Predict(GuessWord)

    async def next_guess(self) -> Guess:
        with dspy.context(lm=self.lm):
            coro = self.guess_fn.aforward(
                history=self.game.history(),  # type: ignore[attr-defined]
                player_id=self.player_id,
                player_personality=self.player_personality
            )
            result = await self.run(coro)
        return Guess(guess=result.guess, rationale=result.rationale)
    # end() inherited from Player handles pending task cancellation
