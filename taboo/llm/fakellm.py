import asyncio
import random
from typing import List, Tuple

class FakeLLM:
    """A latency-simulating fake model used for V0 demos and tests."""
    def __init__(self, name: str):
        self.name = name

    async def clue(self, target: str, taboo: List[str], history: list) -> str:
        # simulate latency
        await asyncio.sleep(random.uniform(0.15, 0.9))
        # extremely naive clue generation (avoid taboo words by redaction)
        base = f"Common thing related to {target[0].upper()} and {len(target)} letters."
        for t in taboo:
            base = base.replace(t, "[redacted]")
        return base

    async def guess(self, clues: List[str], other_guesses: List[str]) -> Tuple[str, str]:
        await asyncio.sleep(random.uniform(0.2, 1.1))
        # naive: derive a guess based on letters mentioned or random nouns
        nouns = ["apple","table","river","python","guitar","window","planet","coffee"]
        # tilt toward words appearing in clues (first letter hints)
        letter = None
        for c in reversed(clues[-3:]):
            for ch in c:
                if ch.isalpha():
                    letter = ch.lower()
                    break
            if letter:
                break
        if letter:
            options = [n for n in nouns if n.startswith(letter)] or nouns
        else:
            options = nouns
        guess = random.choice(options)
        rationale = f"Based on clues and letter '{letter}'" if letter else "Heuristic guess"
        return guess, rationale
