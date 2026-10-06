"""
Core Pydantic data models and schemas for the Vessel System.
Ensures strong typing, serialization, and deterministic validation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Rank(str, Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"
    SS = "SS"
    SSS = "SSS"


class QuestType(str, Enum):
    DAILY = "DAILY"
    MAIN = "MAIN"
    SIDE = "SIDE"
    SPECIAL = "SPECIAL"
    BOSS = "BOSS"


class QuestStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SkillCategory(str, Enum):
    INTELLECT = "INTELLECT"
    TECHNICAL = "TECHNICAL"
    PHYSICAL = "PHYSICAL"
    DISCIPLINE = "DISCIPLINE"
    COMMUNICATION = "COMMUNICATION"
    LEARNING = "LEARNING"
    ADAPTABILITY = "ADAPTABILITY"
    CREATIVE = "CREATIVE"
    STRATEGIC = "STRATEGIC"


class SystemEventType(str, Enum):
    PLAYER_INITIALIZED = "PLAYER_INITIALIZED"
    QUEST_CREATED = "QUEST_CREATED"
    QUEST_COMPLETED = "QUEST_COMPLETED"
    QUEST_FAILED = "QUEST_FAILED"
    LEVEL_UP = "LEVEL_UP"
    RANK_UP = "RANK_UP"
    SKILL_UNLOCKED = "SKILL_UNLOCKED"
    SKILL_LEVELED = "SKILL_LEVELED"
    ACHIEVEMENT_UNLOCKED = "ACHIEVEMENT_UNLOCKED"
    TITLE_UNLOCKED = "TITLE_UNLOCKED"
    TITLE_EQUIPPED = "TITLE_EQUIPPED"
    BOSS_STARTED = "BOSS_STARTED"
    BOSS_COMPLETED = "BOSS_COMPLETED"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    SYSTEM_ADAPTATION = "SYSTEM_ADAPTATION"
    ACTIVITY_EVALUATED = "ACTIVITY_EVALUATED"


class Stats(BaseModel):
    """
    Core attribute capabilities:
    STR: Physical strength & power
    AGI: Speed, nimbleness & reaction
    VIT: Endurance, health & recovery
    INT: Raw intellect & cognitive capacity
    PER: Perception & detail recognition
    WIL: Willpower & emotional control
    DISC: Discipline & consistent execution
    KNOW: Factual knowledge & domain breadth
    TECH: Technical mastery & craft (e.g. engineering/coding)
    RES: Resilience under stress & adversity
    ADP: Adaptability to novel/unfamiliar situations
    """
    STR: float = Field(default=10.0, ge=1.0)
    AGI: float = Field(default=10.0, ge=1.0)
    VIT: float = Field(default=10.0, ge=1.0)
    INT: float = Field(default=10.0, ge=1.0)
    PER: float = Field(default=10.0, ge=1.0)
    WIL: float = Field(default=10.0, ge=1.0)
    DISC: float = Field(default=10.0, ge=1.0)
    KNOW: float = Field(default=10.0, ge=1.0)
    TECH: float = Field(default=10.0, ge=1.0)
    RES: float = Field(default=10.0, ge=1.0)
    ADP: float = Field(default=10.0, ge=1.0)

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()


class PlayerState(BaseModel):
    player_id: str
    name: str = "Player"
    level: int = Field(default=1, ge=1)
    total_xp: int = Field(default=0, ge=0)
    rank: Rank = Rank.E
    gold: int = Field(default=0, ge=0)
    current_streak: int = Field(default=0, ge=0)
    longest_streak: int = Field(default=0, ge=0)
    last_activity_date: Optional[str] = None  # YYYY-MM-DD
    timezone: str = "UTC"
    stats: Stats = Field(default_factory=Stats)
    active_title: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Quest(BaseModel):
    quest_id: str
    player_id: str
    type: QuestType
    title: str
    description: str
    difficulty: Rank = Rank.E
    status: QuestStatus = QuestStatus.ACTIVE
    target: str = "Complete the designated task"
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    xp_reward: int = Field(default=50, ge=0)
    stat_targets: Dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Skill(BaseModel):
    skill_id: str
    player_id: str
    name: str
    description: str
    level: int = Field(default=1, ge=1)
    xp: int = Field(default=0, ge=0)
    category: SkillCategory
    requirements: Dict[str, Any] = Field(default_factory=dict)
    unlocked_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Achievement(BaseModel):
    achievement_id: str
    player_id: str
    name: str
    description: str
    category: str = "MILESTONE"
    unlocked_at: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Title(BaseModel):
    title_id: str
    player_id: str
    name: str
    description: str
    perks: Dict[str, Any] = Field(default_factory=dict)
    unlocked_at: datetime = Field(default_factory=utc_now)


class XPTransaction(BaseModel):
    transaction_id: str
    player_id: str
    amount: int
    source: str
    reference_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Activity(BaseModel):
    activity_id: str
    player_id: str
    type: str
    description: str
    duration_minutes: int = Field(default=1, ge=1)
    difficulty: Rank = Rank.E
    evidence: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActivityEvaluationResult(BaseModel):
    activity_id: str
    player_id: str
    quality: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    completion: float = Field(ge=0.0, le=1.0)
    consistency: float = Field(ge=0.0, le=1.0)
    capability_gain: Dict[str, float] = Field(default_factory=dict)
    awarded_xp: int = Field(ge=0)
    feedback: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class SystemEvent(BaseModel):
    event_id: str
    player_id: str
    event_type: SystemEventType
    description: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, str]
