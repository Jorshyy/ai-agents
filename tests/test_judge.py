import pytest
from unittest.mock import AsyncMock
from taboo.agents.judge import AIJudge

@pytest.mark.asyncio
@pytest.mark.parametrize("guess,target,expected", [
    ("apple", "apple", True),
    ("banana", "apple", False),
])
async def test_check_guess(mocker, guess, target, expected):
    judge = AIJudge()
    mocker.patch.object(judge.checker, "aforward", return_value=AsyncMock(is_correct=expected))
    judge._game = AsyncMock(target=target)
    result = await judge.check_guess(guess)
    assert result == expected
