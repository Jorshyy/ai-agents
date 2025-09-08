from __future__ import annotations

from pydantic import BaseModel
import dspy


class CreateCard(dspy.Signature):
    """
    You are creating a game card for the game Taboo. Each card has a target word
    and a list of taboo words. One of the players ("the cluer") will try to get
    the other players to guess the target word by giving clues, but they cannot
    use any of the taboo words in their clues, or they lose.

    For example, if the target word is "apple", the taboo words might be
    ["fruit", "red", "pie", "tree", "juice"].

    Your task is to come up with a target word and a list of 5 taboo words
    that will make the game interesting and challenging. The taboo words should ideally
    be the most obvious clues to the target word, so that the cluer has to be creative.
    """
    target: str = dspy.OutputField(description="The target word for the game")
    taboo_words: list[str] = dspy.OutputField(description="A list of taboo words that cannot be used in clues for the target word") 


create_card = dspy.ChainOfThought(CreateCard)


class CreateTabooWords(dspy.Signature):
    """
    You are creating a game card for the game Taboo. Each card has a target word
    and a list of taboo words. One of the players ("the cluer") will try to get
    the other players to guess the target word by giving clues, but they cannot
    use any of the taboo words in their clues, or they lose.

    For example, if the target word is "apple", the taboo words might be
    ["fruit", "red", "pie", "tree", "juice"].

    You will be given a target word. Your task is to come up with a list of 5 taboo words
    that will make the game interesting and challenging. The taboo words should ideally
    be the most obvious clues to the target word, so that the cluer has to be creative.
    """
    target: str = dspy.InputField(description="The target word for the game")
    taboo_words: list[str] = dspy.OutputField(description="A list of taboo words that cannot be used in clues for the target word") 


create_taboo_words = dspy.ChainOfThought(CreateTabooWords)


lm = dspy.LM(model="gemini/gemini-2.5-pro", max_tokens=20_000, temperature=1.0, cache=False)

class TabooCard(BaseModel):
    target: str
    taboo_words: list[str]

    @staticmethod
    def generate() -> TabooCard:
        with dspy.context(lm=lm):
            result = create_card()
        return TabooCard(target=result.target, taboo_words=result.taboo_words)
    
    @staticmethod
    def from_target(target: str) -> TabooCard:
        with dspy.context(lm=lm):
            result = create_taboo_words(target=target)
        return TabooCard(target=target, taboo_words=result.taboo_words)