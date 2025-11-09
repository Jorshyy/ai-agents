# tests/test_player.py
import asyncio
import pytest

from taboo.player import Cluer, Guesser, Buzzer, Judge, Guess 
from taboo.types import ClueEvent 

@pytest.fixture
def fake_game():
    class FakeGame:
        def __init__(self):
            self.events = []
            self._over = False
        async def publish(self, ev):
            self.events.append(ev)
        def is_over(self):
            return self._over
        def end(self, reason: str, winner: str | None = None):
            self._over = True
            self.events.append({"role": "system", "reason": reason, "winner": winner})
    return FakeGame()

# Minimal concrete subclasses (to satisfy abstract methods)
class DummyCluer(Cluer):
    async def next_clue(self) -> str:
        return "Aura"

class DummyGuesser(Guesser):
    def __init__(self):
        super().__init__("g1")
    async def next_guess(self) -> Guess:
        # not used in these tests
        await asyncio.sleep(0)
        return Guess(guess="")

class DummyBuzzer(Buzzer):
    async def _violates(self, text: str) -> str | None:
        return None

class DummyJudge(Judge):
    async def check_guess(self, guess: str) -> bool:
        return True

@pytest.mark.asyncio
async def test_player_announce_appends_to_history(fake_game):
    p = DummyCluer().join(fake_game)   
    await p.announce(ClueEvent(role="cluer", clue="Aura")) 
    assert fake_game.events and getattr(fake_game.events[-1], "role", None) == "cluer"

@pytest.mark.asyncio
async def test_player_run_cancels_when_game_over(mocker, fake_game):
    p = DummyGuesser().join(fake_game)
    async def long_task():
        await asyncio.sleep(999)
    cancel_spy = mocker.spy(asyncio.Task, "cancel")
    task = asyncio.create_task(p.run(long_task()))
    await asyncio.sleep(0)       
    await p.end()          
    await asyncio.sleep(0)
    assert cancel_spy.call_count >= 1
    fake_game.end("timeout")
    assert fake_game.is_over()

@pytest.mark.asyncio
async def test_is_over_delegates_to_game_state(mocker, fake_game):
    p = DummyBuzzer().join(fake_game)
    fake_game.end("timeout")
    assert p.game.is_over() is True

def test_judge_has_expected_api(fake_game):
    j = DummyJudge().join(fake_game)
    assert hasattr(j, "announce")
    assert hasattr(j, "run")
    assert hasattr(j, "game")     
