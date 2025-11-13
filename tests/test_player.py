import asyncio
import pytest

from taboo.player import Cluer, Guesser, Buzzer, Judge, Guess
from taboo.types import ClueEvent


@pytest.fixture
def simple_game():
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


class SimpleCluer(Cluer):
    async def next_clue(self) -> str:
        return "Aura"


class SimpleGuesser(Guesser):
    def __init__(self):
        super().__init__("g1")

    async def next_guess(self) -> Guess:
        # Not needed for these tests; yield once and return an empty guess.
        await asyncio.sleep(0)
        return Guess(guess="")


class SimpleBuzzer(Buzzer):
    async def _violates(self, text: str) -> str | None:
        return None


class SimpleJudge(Judge):
    async def check_guess(self, guess: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_player_announce_appends_to_history(simple_game):
    player = SimpleCluer().join(simple_game)
    await player.announce(ClueEvent(role="cluer", clue="Aura"))
    assert simple_game.events and getattr(simple_game.events[-1], "role", None) == "cluer"


@pytest.mark.asyncio
async def test_player_run_cancels_when_game_over(mocker, simple_game):
    player = SimpleGuesser().join(simple_game)

    async def long_task():
        await asyncio.sleep(999)

    task = asyncio.create_task(player.run(long_task()))
    await asyncio.sleep(0)
    await player.end()
    await asyncio.sleep(0)
    assert task.cancelled() or (task.done() and isinstance(task.exception(), asyncio.CancelledError))

    simple_game.end("timeout")
    assert simple_game.is_over()


@pytest.mark.asyncio
async def test_is_over_delegates_to_game_state(mocker, simple_game):
    player = SimpleBuzzer().join(simple_game)
    simple_game.end("timeout")
    assert player.game.is_over() == True


def test_judge_has_expected_api(simple_game):
    judge = SimpleJudge().join(simple_game)
    assert hasattr(judge, "announce")
    assert hasattr(judge, "run")
    assert hasattr(judge, "game")
