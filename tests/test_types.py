# tests/test_types.py
import pytest
from pydantic import ValidationError

from taboo.types import ClueEvent, BuzzEvent, GuessEvent, JudgeEvent

@pytest.mark.parametrize(
    "payload, model",
    [
        ({"role": "cluer", "clue": "A hint"}, ClueEvent),
        ({"role": "buzzer", "clue": "A hint", "violates_taboo": True}, BuzzEvent),
        ({"role": "guesser", "player_id": "g1", "guess": "apple"}, GuessEvent),
        ({"role": "judge", "guess": "apple", "is_correct": True}, JudgeEvent),
    ],
)
def test_event_models_accept_valid_payloads(payload, model):
    obj = model(**payload)
    for k, v in payload.items():
        assert getattr(obj, k) == v

@pytest.mark.parametrize(
    "payload, model",
    [
        ({"role": "cluer"}, ClueEvent),  # missing clue
        ({"role": "buzzer"}, BuzzEvent),
        ({"role": "guesser", "guess": "x"}, GuessEvent),  # missing player_id
        ({"role": "judge", "guess": "x"}, JudgeEvent),  # missing is_correct
    ],
)
def test_event_models_reject_missing_required_fields(payload, model):
    with pytest.raises(ValidationError):
        model(**payload)

@pytest.mark.parametrize(
    "payload, model",
    [
        ({"role": "cluer", "clue": 123}, ClueEvent),  # wrong type
        ({"role": "buzzer", "clue": "x", "violates_taboo": ["yes"]}, BuzzEvent),
        ({"role": "guesser", "player_id": 7, "guess": "x"}, GuessEvent),
        ({"role": "judge", "guess": "x", "is_correct": "true"}, JudgeEvent),
    ],
)
def test_event_models_reject_wrong_types(payload, model):
    with pytest.raises(ValidationError):
        model(**payload)
