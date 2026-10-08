"""Domain vocabulary; independent of Streamlit and SQLite."""
from enum import StrEnum
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

class State(StrEnum):
    SETUP = 'SETUP'
    READY = 'READY_FOR_NEXT_RUN'
    ACTIVE = 'RUN_ACTIVE'
    WHEEL = 'AWAITING_WHEEL'
    ENDED = 'RUN_ENDED'
    MVP = 'SELECTING_RUN_MVP'
    ELIMINATION = 'PROCESSING_ELIMINATION'
    MELTDOWN = 'PROCESSING_MELTDOWN'
    MOVES = 'RESOLVING_BANKED_MOVES'
    REBUILD = 'ROSTER_RECONSTRUCTION'
    VALIDATION = 'ROSTER_VALIDATION'

class RuleError(ValueError):
    """A rejected operation, safe to display to a user."""

@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    @property
    def valid(self) -> bool:
        return not self.errors

ACTIVE_AREAS = {'lineup', 'bench', 'rotation', 'bullpen'}
POSITIONS = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'SP', 'RP']
AREAS = ['lineup', 'bench', 'rotation', 'bullpen', 'minors', 'dfa']

def uid() -> str:
    return str(uuid4())

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

# Typed service DTOs, separate from the repository's JSON encoding.
from typing import TypedDict, Literal, NotRequired

class PlayerCard(TypedDict):
    id: str
    franchise_id: str
    name: str
    version: str
    ovr: int
    primary: str
    secondary: list[str]
    kind: Literal['hitter', 'pitcher']
    area: str
    position: str
    order: int
    eligibility: Literal['legal', 'illegal', 'unknown']
    protected: bool
    hot_seat: bool
    acquired_at: str
    notes: str

class EventRun(TypedDict):
    id: str
    franchise_id: str
    number: int
    event: str
    wins: int
    losses: int
    max_losses: int
    roster_ids: list[str]
    started_at: str
    ended_at: str | None
    mvp: str | None
    settings: dict

class WheelJob(TypedDict):
    id: str
    wheel_id: str
    source: str
    game_id: str | None
    target: str | None
    depth: int
    parent_spin: NotRequired[str]
    constraints: NotRequired[list[str]]
