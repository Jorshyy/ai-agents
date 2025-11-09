import asyncio
import pytest

from taboo.game import Game
from taboo.player import Cluer, Guesser, Buzzer, Judge

class FakeCluer(Cluer):
    async def act(self):
        # can be overridden per scenario; default is a neutral clue
        self.announce({"role": "cluer", "clue": "Aura"})

class FakeGuesser(Guesser):
    def __init__(self, *a, guess=None, **kw):
        super().__init__(*a, **kw)
        self._guess = guess

    async def act(self):
        if self._guess:
            self.announce({"role": "guesser", "player_id": self.name, "guess": self._guess})

class FakeBuzzer(Buzzer):
    def __init__(self, *a, allow=True, **kw):
        super().__init__(*a, **kw)
        self._allow = allow

    async def act(self):
        # mirror the last cluer clue, decide allowed/disallowed
        last_clue = next((e["clue"] for e in reversed(self.game.history) if e["role"] == "cluer"), "x")
        self.announce({"role": "buzzer", "clue": last_clue, "allowed": self._allow})

class FakeJudge(Judge):
    def __init__(self, *a, correct=False, **kw):
        super().__init__(*a, **kw)
        self._correct = correct

    async def act(self):
        # judge the last guess
        last_guess = next((e["guess"] for e in reversed(self.game.history) if e["role"] == "guesser"), "x")
        self.announce({"role": "judge", "guess": last_guess, "is_correct": self._correct})

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
    # short game
    game = Game(target="apple", duration=0.05)

    cluer = FakeCluer(game=game, name="cluer")
    buzzer = FakeBuzzer(game=game, name="buzzer", **players_kwargs.get("buzzer", {}))
    judge = FakeJudge(game=game, name="judge", **players_kwargs.get("judge", {}))
    guesser = FakeGuesser(game=game, name="guesser", **players_kwargs.get("guesser", {}))

    tasks = [asyncio.create_task(p.run(p.act())) for p in (cluer, buzzer, judge, guesser)]

    # the game coordinator should decide the end on history
    await asyncio.sleep(0.05 if scenario == "timeout" else 0.0)

    end_event = next(e for e in reversed(game.history) if e.get("role") == "system")
    assert end_event["reason"] == expected_reason
    # cleanup
    for t in tasks:
        t.cancel()
