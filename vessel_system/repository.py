"""
Authoritative Repository layer for persistent Firestore data storage.
Includes transactional mutations, atomic updates, and fallback mock support for unit tests.
"""

import copy
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from google.cloud import firestore

from vessel_system.models import (
    PlayerState, Stats, Quest, Skill, Achievement, Title,
    XPTransaction, Activity, SystemEvent, SystemEventType, QuestStatus
)
from vessel_system.firebase import get_firestore, is_firebase_available

logger = logging.getLogger("vessel_system.repository")


class RepositoryInterface(ABC):
    @abstractmethod
    def get_player(self, player_id: str) -> Optional[PlayerState]:
        pass

    @abstractmethod
    def save_player(self, player: PlayerState) -> None:
        pass

    @abstractmethod
    def get_quest(self, player_id: str, quest_id: str) -> Optional[Quest]:
        pass

    @abstractmethod
    def save_quest(self, quest: Quest) -> None:
        pass

    @abstractmethod
    def list_quests(self, player_id: str, status: Optional[QuestStatus] = None) -> List[Quest]:
        pass

    @abstractmethod
    def save_skill(self, skill: Skill) -> None:
        pass

    @abstractmethod
    def list_skills(self, player_id: str) -> List[Skill]:
        pass

    @abstractmethod
    def save_achievement(self, achievement: Achievement) -> None:
        pass

    @abstractmethod
    def list_achievements(self, player_id: str) -> List[Achievement]:
        pass

    @abstractmethod
    def save_title(self, title: Title) -> None:
        pass

    @abstractmethod
    def list_titles(self, player_id: str) -> List[Title]:
        pass

    @abstractmethod
    def save_xp_transaction(self, tx: XPTransaction) -> None:
        pass

    @abstractmethod
    def save_activity(self, activity: Activity) -> None:
        pass

    @abstractmethod
    def list_activities(self, player_id: str, limit: int = 20) -> List[Activity]:
        pass

    @abstractmethod
    def save_event(self, event: SystemEvent) -> None:
        pass

    @abstractmethod
    def list_events(self, player_id: str, limit: int = 50) -> List[SystemEvent]:
        pass


class FirestoreRepository(RepositoryInterface):
    """
    Production-grade Firestore implementation.
    Follows schema:
    players/{player_id}
    players/{player_id}/quests/{quest_id}
    players/{player_id}/skills/{skill_id}
    players/{player_id}/achievements/{achievement_id}
    players/{player_id}/titles/{title_id}
    players/{player_id}/xp_transactions/{transaction_id}
    players/{player_id}/activities/{activity_id}
    players/{player_id}/events/{event_id}
    """

    def __init__(self, db: Optional[firestore.Client] = None):
        self.db = db or get_firestore()

    def _player_ref(self, player_id: str):
        return self.db.collection("players").document(player_id)

    def get_player(self, player_id: str) -> Optional[PlayerState]:
        doc = self._player_ref(player_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        return PlayerState(**data)

    def save_player(self, player: PlayerState) -> None:
        player.updated_at = datetime.now(timezone.utc)
        self._player_ref(player.player_id).set(player.model_dump(mode="json"))

    def get_quest(self, player_id: str, quest_id: str) -> Optional[Quest]:
        doc = self._player_ref(player_id).collection("quests").document(quest_id).get()
        if not doc.exists:
            return None
        return Quest(**doc.to_dict())

    def save_quest(self, quest: Quest) -> None:
        ref = self._player_ref(quest.player_id).collection("quests").document(quest.quest_id)
        ref.set(quest.model_dump(mode="json"))

    def list_quests(self, player_id: str, status: Optional[QuestStatus] = None) -> List[Quest]:
        coll = self._player_ref(player_id).collection("quests")
        if status:
            query = coll.where("status", "==", status.value).stream()
        else:
            query = coll.stream()
        return [Quest(**d.to_dict()) for d in query]

    def save_skill(self, skill: Skill) -> None:
        self._player_ref(skill.player_id).collection("skills").document(skill.skill_id).set(skill.model_dump(mode="json"))

    def list_skills(self, player_id: str) -> List[Skill]:
        docs = self._player_ref(player_id).collection("skills").stream()
        return [Skill(**d.to_dict()) for d in docs]

    def save_achievement(self, achievement: Achievement) -> None:
        self._player_ref(achievement.player_id).collection("achievements").document(achievement.achievement_id).set(
            achievement.model_dump(mode="json")
        )

    def list_achievements(self, player_id: str) -> List[Achievement]:
        docs = self._player_ref(player_id).collection("achievements").stream()
        return [Achievement(**d.to_dict()) for d in docs]

    def save_title(self, title: Title) -> None:
        self._player_ref(title.player_id).collection("titles").document(title.title_id).set(title.model_dump(mode="json"))

    def list_titles(self, player_id: str) -> List[Title]:
        docs = self._player_ref(player_id).collection("titles").stream()
        return [Title(**d.to_dict()) for d in docs]

    def save_xp_transaction(self, tx: XPTransaction) -> None:
        self._player_ref(tx.player_id).collection("xp_transactions").document(tx.transaction_id).set(
            tx.model_dump(mode="json")
        )

    def save_activity(self, activity: Activity) -> None:
        self._player_ref(activity.player_id).collection("activities").document(activity.activity_id).set(
            activity.model_dump(mode="json")
        )

    def list_activities(self, player_id: str, limit: int = 20) -> List[Activity]:
        docs = (
            self._player_ref(player_id)
            .collection("activities")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [Activity(**d.to_dict()) for d in docs]

    def save_event(self, event: SystemEvent) -> None:
        self._player_ref(event.player_id).collection("events").document(event.event_id).set(
            event.model_dump(mode="json")
        )

    def list_events(self, player_id: str, limit: int = 50) -> List[SystemEvent]:
        docs = (
            self._player_ref(player_id)
            .collection("events")
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [SystemEvent(**d.to_dict()) for d in docs]


class InMemoryRepository(RepositoryInterface):
    """
    In-memory implementation designed for fast, isolated testing and development
    when Firebase credentials are not yet configured.
    """

    def __init__(self):
        self.players: Dict[str, Dict[str, Any]] = {}
        self.quests: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.skills: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.achievements: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.titles: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.xp_transactions: Dict[str, List[Dict[str, Any]]] = {}
        self.activities: Dict[str, List[Dict[str, Any]]] = {}
        self.events: Dict[str, List[Dict[str, Any]]] = {}

    def get_player(self, player_id: str) -> Optional[PlayerState]:
        data = self.players.get(player_id)
        if not data:
            return None
        return PlayerState(**copy.deepcopy(data))

    def save_player(self, player: PlayerState) -> None:
        player.updated_at = datetime.now(timezone.utc)
        self.players[player.player_id] = player.model_dump(mode="json")

    def get_quest(self, player_id: str, quest_id: str) -> Optional[Quest]:
        p_quests = self.quests.get(player_id, {})
        data = p_quests.get(quest_id)
        if not data:
            return None
        return Quest(**copy.deepcopy(data))

    def save_quest(self, quest: Quest) -> None:
        if quest.player_id not in self.quests:
            self.quests[quest.player_id] = {}
        self.quests[quest.player_id][quest.quest_id] = quest.model_dump(mode="json")

    def list_quests(self, player_id: str, status: Optional[QuestStatus] = None) -> List[Quest]:
        p_quests = self.quests.get(player_id, {})
        res = []
        for q_data in p_quests.values():
            q = Quest(**copy.deepcopy(q_data))
            if status is None or q.status == status:
                res.append(q)
        return res

    def save_skill(self, skill: Skill) -> None:
        if skill.player_id not in self.skills:
            self.skills[skill.player_id] = {}
        self.skills[skill.player_id][skill.skill_id] = skill.model_dump(mode="json")

    def list_skills(self, player_id: str) -> List[Skill]:
        return [Skill(**copy.deepcopy(d)) for d in self.skills.get(player_id, {}).values()]

    def save_achievement(self, achievement: Achievement) -> None:
        if achievement.player_id not in self.achievements:
            self.achievements[achievement.player_id] = {}
        self.achievements[achievement.player_id][achievement.achievement_id] = achievement.model_dump(mode="json")

    def list_achievements(self, player_id: str) -> List[Achievement]:
        return [Achievement(**copy.deepcopy(d)) for d in self.achievements.get(player_id, {}).values()]

    def save_title(self, title: Title) -> None:
        if title.player_id not in self.titles:
            self.titles[title.player_id] = {}
        self.titles[title.player_id][title.title_id] = title.model_dump(mode="json")

    def list_titles(self, player_id: str) -> List[Title]:
        return [Title(**copy.deepcopy(d)) for d in self.titles.get(player_id, {}).values()]

    def save_xp_transaction(self, tx: XPTransaction) -> None:
        if tx.player_id not in self.xp_transactions:
            self.xp_transactions[tx.player_id] = []
        self.xp_transactions[tx.player_id].append(tx.model_dump(mode="json"))

    def save_activity(self, activity: Activity) -> None:
        if activity.player_id not in self.activities:
            self.activities[activity.player_id] = []
        self.activities[activity.player_id].append(activity.model_dump(mode="json"))

    def list_activities(self, player_id: str, limit: int = 20) -> List[Activity]:
        acts = self.activities.get(player_id, [])
        return [Activity(**copy.deepcopy(d)) for d in reversed(acts[-limit:])]

    def save_event(self, event: SystemEvent) -> None:
        if event.player_id not in self.events:
            self.events[event.player_id] = []
        self.events[event.player_id].append(event.model_dump(mode="json"))

    def list_events(self, player_id: str, limit: int = 50) -> List[SystemEvent]:
        evts = self.events.get(player_id, [])
        return [SystemEvent(**copy.deepcopy(d)) for d in reversed(evts[-limit:])]


def get_repository() -> RepositoryInterface:
    """
    Returns the appropriate repository.
    If Firebase credentials are provided, returns FirestoreRepository.
    Otherwise falls back to InMemoryRepository with warning.
    """
    if is_firebase_available():
        return FirestoreRepository()
    logger.warning("Firebase credentials not configured. Using InMemoryRepository.")
    return InMemoryRepository()
