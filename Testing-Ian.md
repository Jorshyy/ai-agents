# Testing Overview

## Custom Exceptions

- **CardGenerationError**: Raised when DSPy or LLM fails to generate a valid taboo card.
  - Example: When DSPy returns malformed data or an empty card.
  
- **InvalidTabooCardError**: Raised when taboo words are invalid or duplicated.
  - Example: If DSPy generates taboo words that are too similar to the target or invalid.

## Tests

### Test for `cluer.py`:
- **Purpose**: Mock the LLM to generate clues and verify that they do not use taboo words.
- **Tools Used**: `pytest`, `pytest-mock`
  
### Test for `judge.py`:
- **Purpose**: Test the `check_guess()` method using parameterized test cases.
- **Tools Used**: `pytest.mark.parametrize`, `pytest-mock`
  
### Test Coverage
- **Functionality**: We test for correct and incorrect guesses in `judge.py` and valid clue generation in `cluer.py`.
- **Edge Cases**: Incorrect, empty, or invalid clues and guesses.
