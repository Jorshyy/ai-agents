import asyncio
import pytest
from taboo.game import Game
from taboo.player import Cluer, Guesser, Buzzer, Judge, Guess

class FakeCluer(Cluer):
    async def next_clue(self) -> str:
        return "Aura"

class FakeGuesser(Guesser):
    def __init__(self, player_id: str, guess=None):
        super().__init__(player_id)
        self._guess = guess
        self._used = False
    async def next_guess(self) -> Guess:
        if self._used or not self._guess:
            await asyncio.sleep(3600)
            return Guess(guess="")
        self._used = True
        return Guess(guess=self._guess)

class FakeBuzzer(Buzzer):
    def __init__(self, violate=False):
        super().__init__()
        self._violate = violate
    async def _violates(self, text: str) -> str | None:
        return "taboo" if self._violate else None

class FakeJudge(Judge):
    def __init__(self, correct=False):
        super().__init__()
        self._correct = correct
    async def check_guess(self, guess: str) -> bool:
        return self._correct

@pytest.mark.parametrize(
    "scenario, players_kwargs, expected_reason",
    [
        ("correct",  {"judge": {"correct": True}, "guesser": {"guess": "apple"}}, "correct"),
        ("buzzed",   {"buzzer": {"allow": False}, "guesser": {"guess": "apple"}}, "buzzed"),
        ("timeout",  {"buzzer": {"allow": True}}, "timeout"),
    ],
)
@pytest.mark.asyncio
async def test_game_end_conditions(mocker, scenario, players_kwargs, expected_reason):
    mocker.patch("asyncio.sleep", side_effect=lambda *_: asyncio.sleep(0))
    
    duration = 0 if scenario == "timeout" else 60
    cluer  = FakeCluer()
    buzzer = FakeBuzzer(**players_kwargs.get("buzzer", {}))
    judge  = FakeJudge(**players_kwargs.get("judge", {}))
    guesser = FakeGuesser("g1", **players_kwargs.get("guesser", {}))
    game = Game(target="apple", taboo_words=[], players=[cluer, buzzer, judge, guesser], duration_sec=duration)
    # start and finish the round
    await game.play()
    end_event = next(e for e in reversed(game.events) if getattr(e, "role", "") == "system" and getattr(e, "event", "") == "end")
    assert getattr(end_event, "reason", None) == expected_reason
