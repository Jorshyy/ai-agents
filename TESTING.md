# Testing Overview


## How to run tests
```
uv venv
source .venv/bin/activate
uv pip install .
uv pip install --group tool
uv run pytest
```


## Created/Modified Files

### `test_cluer.py`
  
### `test_judge.py`

### `test_game.py`

### `test_player.py`

### `test_types.py`

### `card_creator.py`

### `game.py`

### `types.py`


## Custom Exceptions

- **CardGenerationError**: Raised when DSPy or LLM fails to generate a valid taboo card.
  - Example: When DSPy returns malformed data or an empty card.
  
- **InvalidTabooCardError**: Raised when taboo words are invalid or duplicated.
  - Example: If DSPy generates taboo words that are too similar to the target or invalid.


  
### Test Coverage
- **Functionality**: We test for correct and incorrect guesses in `judge.py` and valid clue generation in `cluer.py`.
- **Edge Cases**: Incorrect, empty, or invalid clues and guesses.
