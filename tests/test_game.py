import asyncio
import pytest

from taboo.game import Game
from taboo.player import Cluer, Guesser, Buzzer, Judge, Guess


class SimpleCluer(Cluer):
    def __init__(self):
        super().__init__()
        self.sent_first_clue = False

    async def next_clue(self) -> str:
        # yield once so other tasks get a chance to run.
        await asyncio.sleep(0)

        if self.sent_first_clue:
            await asyncio.sleep(3600)
            return "Aura"

        self.sent_first_clue = True
        return "Aura"


class SimpleBuzzer(Buzzer):
    def __init__(self, allow=True):
        super().__init__()
        self.allow_violations = allow

    async def _violates(self, text: str) -> str | None:
        return None if self.allow_violations else "taboo"


class SimpleGuesser(Guesser):
    def __init__(self, guess=None):
        super().__init__("g1")
        self.next_guess_text = guess
        self.already_guessed = False

    async def next_guess(self) -> Guess:
        if self.already_guessed or not self.next_guess_text:
            await asyncio.sleep(3600)
            return Guess(guess="")

        self.already_guessed = True
        await asyncio.sleep(0)
        return Guess(guess=self.next_guess_text)


class SimpleJudge(Judge):
    def __init__(self, correct=False):
        super().__init__()
        self.correct_answer = correct

    async def check_guess(self, guess: str) -> bool:
        return self.correct_answer


@pytest.mark.parametrize(
    "scenario, players_kwargs, expected_reason",
    [
        ("correct", {"judge": {"correct": True}, "guesser": {"guess": "apple"}}, "correct"),
        ("buzzed", {"buzzer": {"allow": False}, "guesser": {"guess": "apple"}}, "buzzed"),
        ("timeout", {"buzzer": {"allow": True}}, "timeout"),
    ],
)
@pytest.mark.asyncio
async def test_game_end_conditions(mocker, scenario, players_kwargs, expected_reason):
    """Confirm the game ends for the correct reasons in different scenarios.

    Scenarios:
    - 'correct': judge marks the guess correct
    - 'buzzed': buzzer detects a taboo violation
    - 'timeout': no guess happens before the duration expires
    """
    duration_seconds = 0 if scenario == "timeout" else 2

    cluer = SimpleCluer()
    buzzer = SimpleBuzzer(**players_kwargs.get("buzzer", {}))
    judge = SimpleJudge(**players_kwargs.get("judge", {}))
    guesser = SimpleGuesser(**players_kwargs.get("guesser", {}))

    game = Game(
        target="apple",
        taboo_words=[],
        players=[cluer, buzzer, judge, guesser],
        duration_sec=duration_seconds,
    )

    # run the game and wait for it to finish
    await asyncio.wait_for(game.play(), timeout=2)

    # find the final 'end' system event and check its reason
    end_event = next(
        e for e in reversed(game.events)
        if getattr(e, "role", "") == "system" and getattr(e, "event", "") == "end"
    )

    assert getattr(end_event, "reason", None) == expected_reason

