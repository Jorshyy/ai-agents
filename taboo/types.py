"""
Event types for messaging and game history
"""


from __future__ import annotations
from typing import Literal, Union, Optional, Annotated, List
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    role: str

    model_config = {
        "extra": "forbid"
    }


class ClueEvent(BaseEvent):
    role: Literal["cluer"]
    clue: str


class BuzzEvent(BaseEvent):
    role: Literal["buzzer"]
    clue: str
    reason: Optional[str] = None


class GuessEvent(BaseEvent):
    role: Literal["guesser"]
    player_id: str
    guess: str
    rationale: Optional[str] = None


class JudgeEvent(BaseEvent):
    role: Literal["judge"]
    guess: str
    is_correct: bool
    by: Optional[str] = None


class SystemMessage(BaseEvent):
    role: Literal["system"]
    event: Literal["timeout", "end"]
    reason: Optional[Literal["correct", "timeout", "buzzed"]] = None
    winner: Optional[str] = None


Event = Annotated[Union[ClueEvent, BuzzEvent, GuessEvent, JudgeEvent, SystemMessage], Field(discriminator="role")]
HistoryList = List[Event]
