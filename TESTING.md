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
```
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
taboo/__main__.py                  8      8     0%   1-11
taboo/agents/__init__.py           5      0   100%
taboo/agents/buzzer.py            20     10    50%   20-23, 26-33
taboo/agents/card_creator.py      39     16    59%   65-73, 77-84
taboo/agents/cluer.py             26      6    77%   33-38
taboo/agents/guesser.py           19      8    58%   21-24, 27-34
taboo/agents/judge.py             20      1    95%   26
taboo/cli.py                      67     67     0%   1-101
taboo/game.py                     97      7    93%   19, 21, 23, 25, 57, 121-122
taboo/human.py                    19     19     0%   4-33
taboo/player.py                   99      9    91%   34, 70, 85, 97, 127, 135-136, 142, 151
taboo/types.py                    31      0   100%
------------------------------------------------------------
TOTAL                            450    151    66%
```