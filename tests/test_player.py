import asyncio
import pytest

from taboo.player import Cluer, Guesser, Buzzer, Judge
from taboo.types import ClueEvent, Guess

@pytest.fixture
def fake_game():
    class FakeGame:
        def __init__(self):
            self.history = []
            self._over = False
        
        async def publish(self, ev):
            self.history.append(ev)
        
        def is_over(self):
            return self._over

        @property
        def over(self):
            return self._over

        def end(self, reason: str, winner: str | None = None):
            self._over = True
            self.history.append({"role": "system", "reason": reason, "winner": winner})

    return FakeGame()

class FakeCluer(Cluer):
    async def next_clue(self) -> str:
        return "Aura"

class FakeGuesser(Guesser):
    def __init__(self):
        super().__init__("g1")
    async def next_guess(self) -> Guess:
        return Guess(guess="")

class FakeJudge(Judge):
    async def check_guess(self, guess: str) -> bool:
        return True

@pytest.mark.asyncio
async def test_player_announce_appends_to_history(fake_game):
    cluer = FakeCluer().join(fake_game)
    await cluer.announce(ClueEvent(role="cluer", clue="Aura"))
    assert fake_game.history and getattr(fake_game.history[-1], "role", None) == "cluer"
 

@pytest.mark.asyncio
async def test_player_run_cancels_when_game_over(mocker, fake_game):
    guesser = FakeGuesser().join(fake_game)

    async def long_task():
        await asyncio.sleep(999)

    cancel_spy = mocker.spy(asyncio.Task, "cancel")

    task = asyncio.create_task(guesser.run(long_task()))
    fake_game.end("timeout")
    # tasks are cancelled when end() is called on the player
    await guesser.end()
    await asyncio.sleep(0) # allow event loop to process

    assert cancel_spy.call_count >= 1
    assert fake_game.over

@pytest.mark.asyncio
async def test_is_over_delegates_to_game_state(mocker, fake_game):
    class DummyBuzzer(Buzzer):
        async def _violates(self, text: str) -> str | None:
            return None
    buzzer = DummyBuzzer().join(fake_game)


    fake_game.end("timeout")
    assert buzzer.game.is_over() is True


def test_judge_has_expected_api(fake_game):
    judge = FakeJudge().join(fake_game)
    assert hasattr(judge, "announce")
    assert hasattr(judge, "run")
    assert hasattr(judge, "game")
