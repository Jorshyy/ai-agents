from unittest.mock import AsyncMock, patch
import pytest
from taboo.agents.cluer import AICluer
from taboo.types import ClueEvent

@pytest.mark.asyncio
async def test_ai_cluer_next_clue_returns_clue():
    cluer = AICluer()
    
    # Patch the read-only property 'game'
    with patch.object(AICluer, 'game', new_callable=AsyncMock) as mock_game:
        mock_game.target = "apple"
        mock_game.taboo_words = ["fruit", "red", "tree"]
        mock_game.history.return_value = []
        
        # Mock run method
        mock_result = AsyncMock()
        mock_result.clue = "orchard"
        cluer.run = AsyncMock(return_value=mock_result)
        
        clue = await cluer.next_clue()
        assert clue == "orchard"
        for taboo in mock_game.taboo_words:
            assert taboo not in clue
