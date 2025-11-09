# tests/test_player.py
import asyncio
import pytest

from taboo.player import Cluer, Guesser, Buzzer, Judge

@pytest.fixture
def fake_game():
    class FakeGame:
        def __init__(self):
            self.history = []
            self._over = False

        @property
        def over(self):
            return self._over

        def end(self, reason: str, winner: str | None = None):
            self._over = True
            self.history.append({"role": "system", "reason": reason, "winner": winner})

    return FakeGame()

def test_player_announce_appends_to_history(fake_game):
    cluer = Cluer(game=fake_game, name="c1")
    cluer.announce({"role": "cluer", "clue": "Aura"})
    assert fake_game.history and fake_game.history[-1]["role"] == "cluer"

@pytest.mark.asyncio
async def test_player_run_cancels_when_game_over(mocker, fake_game):
    guesser = Guesser(game=fake_game, name="g1")

    async def long_task():
        await asyncio.sleep(999)

    cancel_spy = mocker.spy(asyncio.Task, "cancel")

    task = asyncio.create_task(guesser.run(long_task()))
    fake_game.end("timeout")
    await asyncio.sleep(0) # allow event loop to process

    assert cancel_spy.call_count >= 1
    assert fake_game.over

@pytest.mark.asyncio
async def test_is_over_delegates_to_game_state(mocker, fake_game):
    buzzer = Buzzer(game=fake_game, name="b1")
    # Simulate ticking loop until over
    mocker.patch.object(buzzer, "announce", side_effect=lambda e: fake_game.history.append(e))
    fake_game.end("timeout")
    assert buzzer.is_over() is True


def test_judge_has_expected_api(fake_game):
    judge = Judge(game=fake_game, name="j1")
    assert hasattr(judge, "announce")
    assert hasattr(judge, "run")
    assert hasattr(judge, "is_over")
