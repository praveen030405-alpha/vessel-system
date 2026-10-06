"""
Service Layer orchestrating application business logic.
Provides high-level, validated operations for MCP tools and REST endpoints.
"""

from typing import Dict, Any, List, Optional
from vessel_system.engine import VesselEngine
from vessel_system.models import Rank, QuestType, QuestStatus
from vessel_system.firebase import is_firebase_available
from vessel_system.auth import is_auth_enabled


class VesselService:
    def __init__(self, engine: Optional[VesselEngine] = None):
        self.engine = engine or VesselEngine()

    def system_status(self) -> Dict[str, Any]:
        firebase_online = is_firebase_available()
        auth_status = is_auth_enabled()

        return {
            "success": True,
            "status": {
                "mcp": "ONLINE",
                "firebase": "CONNECTED" if firebase_online else "FALLBACK_IN_MEMORY",
                "firestore": "CONNECTED" if firebase_online else "IN_MEMORY_MOCK",
                "authentication": "ENABLED" if auth_status else "DEV_PERMISSIVE",
                "quest_engine": "ONLINE",
                "progression_engine": "ONLINE",
                "weakest_link_engine": "ONLINE",
            }
        }

    def get_player_state(self, player_id: str = "player_1") -> Dict[str, Any]:
        player = self.engine.get_player_state(player_id)
        return {
            "success": True,
            "player": player.model_dump(mode="json")
        }

    def get_stats(self, player_id: str = "player_1") -> Dict[str, Any]:
        player = self.engine.get_player_state(player_id)
        return {
            "success": True,
            "stats": player.stats.to_dict(),
            "level": player.level,
            "rank": player.rank.value,
            "total_xp": player.total_xp,
        }

    def get_weakest_link(self, player_id: str = "player_1") -> Dict[str, Any]:
        analysis = self.engine.get_weakest_link(player_id)
        return {
            "success": True,
            "analysis": analysis.to_dict()
        }

    def get_active_quests(self, player_id: str = "player_1") -> Dict[str, Any]:
        quests = self.engine.repo.list_quests(player_id, status=QuestStatus.ACTIVE)
        return {
            "success": True,
            "active_quests": [q.model_dump(mode="json") for q in quests]
        }

    def get_quest(self, player_id: str, quest_id: str) -> Dict[str, Any]:
        quest = self.engine.repo.get_quest(player_id, quest_id)
        if not quest:
            return {"success": False, "error": {"code": "QUEST_NOT_FOUND", "message": f"Quest {quest_id} not found."}}
        return {
            "success": True,
            "quest": quest.model_dump(mode="json")
        }

    def generate_quest(
        self,
        player_id: str = "player_1",
        target_weakness: Optional[str] = None,
        quest_type_str: str = "DAILY",
        difficulty_str: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            q_type = QuestType(quest_type_str.upper())
        except ValueError:
            q_type = QuestType.DAILY

        diff = None
        if difficulty_str:
            try:
                diff = Rank(difficulty_str.upper())
            except ValueError:
                pass

        quest = self.engine.generate_quest(
            player_id=player_id,
            target_weakness=target_weakness,
            quest_type=q_type,
            difficulty=diff
        )
        return {
            "success": True,
            "quest": quest.model_dump(mode="json")
        }

    def complete_quest(self, player_id: str, quest_id: str) -> Dict[str, Any]:
        return self.engine.complete_quest(player_id, quest_id)

    def fail_quest(self, player_id: str, quest_id: str, reason: str = "Missed due date") -> Dict[str, Any]:
        return self.engine.fail_quest(player_id, quest_id, reason)

    def record_activity(
        self,
        player_id: str,
        activity_type: str,
        description: str,
        duration_minutes: int,
        difficulty_str: str = "E",
        evidence: str = ""
    ) -> Dict[str, Any]:
        try:
            diff = Rank(difficulty_str.upper())
        except ValueError:
            diff = Rank.E

        activity = self.engine.record_activity(
            player_id=player_id,
            activity_type=activity_type,
            description=description,
            duration_minutes=duration_minutes,
            difficulty=diff,
            evidence=evidence
        )
        return {
            "success": True,
            "activity": activity.model_dump(mode="json")
        }

    def evaluate_activity(
        self,
        player_id: str,
        activity_id: str,
        quality_score: float = 1.0,
        completion_score: float = 1.0,
        consistency_score: float = 1.0,
        feedback: str = ""
    ) -> Dict[str, Any]:
        res = self.engine.evaluate_activity(
            player_id=player_id,
            activity_id=activity_id,
            quality_score=quality_score,
            completion_score=completion_score,
            consistency_score=consistency_score,
            feedback=feedback
        )
        return {
            "success": True,
            "evaluation": res.model_dump(mode="json")
        }

    def award_xp(self, player_id: str, amount: int, reason: str = "Manual override") -> Dict[str, Any]:
        """Strictly controlled backend XP adjustment."""
        player = self.engine.get_player_state(player_id)
        old_level = player.level
        old_rank = player.rank
        player.total_xp += max(0, amount)

        from vessel_system.progression import level_from_xp, rank_from_stats
        player.level = level_from_xp(player.total_xp)
        player.rank = rank_from_stats(player.stats, player.level)
        self.engine.repo.save_player(player)

        return {
            "success": True,
            "awarded_xp": amount,
            "total_xp": player.total_xp,
            "level": player.level,
            "rank": player.rank.value,
            "level_up": player.level > old_level,
            "rank_up": player.rank != old_rank,
        }

    def get_skills(self, player_id: str = "player_1") -> Dict[str, Any]:
        skills = self.engine.repo.list_skills(player_id)
        return {
            "success": True,
            "skills": [s.model_dump(mode="json") for s in skills]
        }

    def get_achievements(self, player_id: str = "player_1") -> Dict[str, Any]:
        achs = self.engine.repo.list_achievements(player_id)
        return {
            "success": True,
            "achievements": [a.model_dump(mode="json") for a in achs]
        }

    def get_titles(self, player_id: str = "player_1") -> Dict[str, Any]:
        titles = self.engine.repo.list_titles(player_id)
        return {
            "success": True,
            "titles": [t.model_dump(mode="json") for t in titles]
        }

    def get_history(self, player_id: str = "player_1", limit: int = 50) -> Dict[str, Any]:
        events = self.engine.repo.list_events(player_id, limit=limit)
        return {
            "success": True,
            "events": [e.model_dump(mode="json") for e in events]
        }
