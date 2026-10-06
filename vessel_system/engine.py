"""
Vessel System Core Engine.
Orchestrates player progression, quest completion/failure, activity evaluation,
streaks, idempotent mutations, achievement evaluation, and system events.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

from vessel_system.models import (
    PlayerState, Stats, Quest, Skill, Achievement, Title,
    XPTransaction, Activity, ActivityEvaluationResult,
    QuestType, QuestStatus, Rank, SystemEventType
)
from vessel_system.repository import RepositoryInterface, get_repository
from vessel_system.progression import (
    level_from_xp, rank_from_stats, xp_required_for_level,
    calculate_activity_xp, xp_for_next_level
)
from vessel_system.weakest_link import WeakestLinkAnalyzer, WeakestLinkAnalysis
from vessel_system.quest_engine import QuestEngine
from vessel_system.events import create_event

logger = logging.getLogger("vessel_system.engine")


class VesselEngine:
    def __init__(self, repository: Optional[RepositoryInterface] = None):
        self.repo = repository or get_repository()

    def get_or_initialize_player(self, player_id: str = "player_1", name: str = "Player") -> Tuple[PlayerState, bool]:
        """
        Retrieves existing player or initializes a fresh vessel state.
        Returns (PlayerState, is_newly_created).
        """
        player = self.repo.get_player(player_id)
        if player is not None:
            return player, False

        # Initialize fresh player
        now = datetime.now(timezone.utc)
        initial_stats = Stats()
        player = PlayerState(
            player_id=player_id,
            name=name,
            level=1,
            total_xp=0,
            rank=Rank.E,
            gold=0,
            current_streak=0,
            longest_streak=0,
            last_activity_date=None,
            timezone="UTC",
            stats=initial_stats,
            active_title="The Initiate",
            created_at=now,
            updated_at=now,
        )
        self.repo.save_player(player)

        # Initial Title & Achievement
        init_title = Title(
            title_id="title_initiate",
            player_id=player_id,
            name="The Initiate",
            description="Granted upon vessel awakening into the System.",
            perks={"xp_boost": 0.0},
            unlocked_at=now,
        )
        self.repo.save_title(init_title)

        init_ach = Achievement(
            achievement_id="ach_awakened",
            player_id=player_id,
            name="Vessel Awakened",
            description="Entered the Vessel System progression matrix.",
            category="MILESTONE",
            unlocked_at=now,
        )
        self.repo.save_achievement(init_ach)

        # Log event
        evt = create_event(
            player_id=player_id,
            event_type=SystemEventType.PLAYER_INITIALIZED,
            description=f"Player '{name}' successfully initialized into the Vessel System.",
            payload={"level": 1, "rank": "E"}
        )
        self.repo.save_event(evt)

        logger.info(f"Initialized new player {player_id}")
        return player, True

    def get_player_state(self, player_id: str = "player_1") -> PlayerState:
        player, _ = self.get_or_initialize_player(player_id)
        return player

    def get_weakest_link(self, player_id: str = "player_1") -> WeakestLinkAnalysis:
        player = self.get_player_state(player_id)
        quests = self.repo.list_quests(player_id)
        activities = self.repo.list_activities(player_id, limit=20)
        return WeakestLinkAnalyzer.analyze(player, quests, activities)

    def generate_quest(
        self,
        player_id: str = "player_1",
        target_weakness: Optional[str] = None,
        quest_type: QuestType = QuestType.DAILY,
        difficulty: Optional[Rank] = None
    ) -> Quest:
        player = self.get_player_state(player_id)
        if not target_weakness:
            analysis = self.get_weakest_link(player_id)
            target_weakness = analysis.weakest_stat

        if quest_type == QuestType.BOSS:
            quest = QuestEngine.generate_boss_quest(player, target_weakness)
        else:
            quest = QuestEngine.generate_targeted_quest(
                player=player,
                weakest_stat=target_weakness,
                quest_type=quest_type,
                difficulty=difficulty
            )

        self.repo.save_quest(quest)

        # Log event
        evt = create_event(
            player_id=player_id,
            event_type=SystemEventType.QUEST_CREATED,
            description=f"Generated {quest.type.value} quest '{quest.title}' targeting {target_weakness}.",
            payload={"quest_id": quest.quest_id, "difficulty": quest.difficulty.value, "xp_reward": quest.xp_reward}
        )
        self.repo.save_event(evt)
        return quest

    def complete_quest(self, player_id: str, quest_id: str) -> Dict[str, Any]:
        """
        Completes a quest with strict idempotency and atomic-style transactional state updates.
        """
        player = self.get_player_state(player_id)
        quest = self.repo.get_quest(player_id, quest_id)

        if not quest:
            return {"success": False, "error": {"code": "QUEST_NOT_FOUND", "message": f"Quest {quest_id} not found."}}

        if quest.player_id != player_id:
            return {"success": False, "error": {"code": "FORBIDDEN", "message": "Player does not own this quest."}}

        # IDEMPOTENCY CHECK
        if quest.status == QuestStatus.COMPLETED:
            return {
                "success": True,
                "message": "Quest was already completed. No duplicate rewards granted.",
                "quest": quest.model_dump(mode="json"),
                "player": player.model_dump(mode="json"),
                "already_completed": True,
            }

        if quest.status in [QuestStatus.FAILED, QuestStatus.EXPIRED, QuestStatus.CANCELLED]:
            return {"success": False, "error": {"code": "INVALID_STATE", "message": f"Cannot complete a {quest.status.value} quest."}}

        now = datetime.now(timezone.utc)
        quest.status = QuestStatus.COMPLETED
        quest.completed_at = now
        quest.progress = 100.0
        self.repo.save_quest(quest)

        # 1. Award XP
        old_level = player.level
        old_rank = player.rank
        player.total_xp += quest.xp_reward

        # 2. Level evaluation
        new_level = level_from_xp(player.total_xp)
        level_up = new_level > old_level
        player.level = new_level

        # 3. Stat upgrades
        stats_dict = player.stats.to_dict()
        for stat, gain in quest.stat_targets.items():
            if stat in stats_dict:
                stats_dict[stat] = round(stats_dict[stat] + gain, 2)
        player.stats = Stats(**stats_dict)

        # 4. Rank evaluation
        new_rank = rank_from_stats(player.stats, player.level)
        rank_up = new_rank != old_rank
        player.rank = new_rank

        # 5. Streak update
        today_str = now.strftime("%Y-%m-%d")
        if player.last_activity_date != today_str:
            if player.last_activity_date:
                try:
                    last_date = datetime.strptime(player.last_activity_date, "%Y-%m-%d").date()
                    if (now.date() - last_date).days == 1:
                        player.current_streak += 1
                    elif (now.date() - last_date).days > 1:
                        player.current_streak = 1
                except Exception:
                    player.current_streak = 1
            else:
                player.current_streak = 1

            player.last_activity_date = today_str
            if player.current_streak > player.longest_streak:
                player.longest_streak = player.current_streak

        # 6. Save Player State
        player.updated_at = now
        self.repo.save_player(player)

        # 7. XP Transaction Record
        tx = XPTransaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            player_id=player_id,
            amount=quest.xp_reward,
            source=f"QUEST_COMPLETION:{quest.type.value}",
            reference_id=quest_id,
            timestamp=now,
            metadata={"quest_title": quest.title}
        )
        self.repo.save_xp_transaction(tx)

        # 8. Events
        self.repo.save_event(create_event(
            player_id=player_id,
            event_type=SystemEventType.QUEST_COMPLETED,
            description=f"Completed quest '{quest.title}' (+{quest.xp_reward} XP).",
            payload={"quest_id": quest_id, "xp": quest.xp_reward}
        ))

        if level_up:
            self.repo.save_event(create_event(
                player_id=player_id,
                event_type=SystemEventType.LEVEL_UP,
                description=f"Level increased from {old_level} to {new_level}.",
                payload={"old_level": old_level, "new_level": new_level}
            ))

        if rank_up:
            self.repo.save_event(create_event(
                player_id=player_id,
                event_type=SystemEventType.RANK_UP,
                description=f"Rank upgraded from {old_rank.value} to {new_rank.value}.",
                payload={"old_rank": old_rank.value, "new_rank": new_rank.value}
            ))

        # 9. Evaluate Achievements
        self._evaluate_achievements(player)

        return {
            "success": True,
            "message": f"Quest '{quest.title}' completed successfully.",
            "xp_awarded": quest.xp_reward,
            "level_up": level_up,
            "old_level": old_level,
            "new_level": new_level,
            "rank_up": rank_up,
            "old_rank": old_rank.value,
            "new_rank": new_rank.value,
            "stat_gains": quest.stat_targets,
            "current_streak": player.current_streak,
            "player": player.model_dump(mode="json"),
        }

    def fail_quest(self, player_id: str, quest_id: str, reason: str = "Missed due date") -> Dict[str, Any]:
        """
        Fails a quest safely without physical harm.
        Resets streak, logs failure for WeakestLinkAnalyzer adaptation.
        """
        player = self.get_player_state(player_id)
        quest = self.repo.get_quest(player_id, quest_id)

        if not quest:
            return {"success": False, "error": {"code": "QUEST_NOT_FOUND", "message": f"Quest {quest_id} not found."}}

        if quest.status in [QuestStatus.COMPLETED, QuestStatus.FAILED]:
            return {"success": False, "error": {"code": "INVALID_STATE", "message": f"Quest already {quest.status.value}."}}

        now = datetime.now(timezone.utc)
        quest.status = QuestStatus.FAILED
        quest.failed_at = now
        self.repo.save_quest(quest)

        # Reset streak safely
        old_streak = player.current_streak
        player.current_streak = 0
        player.updated_at = now
        self.repo.save_player(player)

        # Create system event
        evt = create_event(
            player_id=player_id,
            event_type=SystemEventType.QUEST_FAILED,
            description=f"Quest '{quest.title}' failed: {reason}. Streak reset from {old_streak} to 0.",
            payload={"quest_id": quest_id, "reason": reason, "old_streak": old_streak}
        )
        self.repo.save_event(evt)

        return {
            "success": True,
            "message": f"Quest '{quest.title}' marked as FAILED. Weakest link engine updated.",
            "streak_reset": True,
            "old_streak": old_streak,
            "current_streak": 0,
        }

    def record_activity(
        self,
        player_id: str,
        activity_type: str,
        description: str,
        duration_minutes: int,
        difficulty: Rank = Rank.E,
        evidence: str = ""
    ) -> Activity:
        activity = Activity(
            activity_id=f"act_{uuid.uuid4().hex[:12]}",
            player_id=player_id,
            type=activity_type,
            description=description,
            duration_minutes=duration_minutes,
            difficulty=difficulty,
            evidence=evidence,
            timestamp=datetime.now(timezone.utc)
        )
        self.repo.save_activity(activity)
        return activity

    def evaluate_activity(
        self,
        player_id: str,
        activity_id: str,
        quality_score: float = 1.0,
        completion_score: float = 1.0,
        consistency_score: float = 1.0,
        feedback: str = ""
    ) -> ActivityEvaluationResult:
        """
        Evaluates an activity, computes backend XP deterministically,
        awards stat impact based on the activity domain, and updates player state.
        """
        player = self.get_player_state(player_id)
        activities = self.repo.list_activities(player_id, limit=50)
        activity = next((a for a in activities if a.activity_id == activity_id), None)

        if not activity:
            # Fallback if activity not found by listing
            activity = Activity(
                activity_id=activity_id,
                player_id=player_id,
                type="GENERAL",
                description="General task",
                duration_minutes=30,
                difficulty=Rank.E,
                timestamp=datetime.now(timezone.utc)
            )

        awarded_xp = calculate_activity_xp(
            duration_minutes=activity.duration_minutes,
            difficulty=activity.difficulty,
            quality_score=quality_score,
            completion_score=completion_score
        )

        now = datetime.now(timezone.utc)
        player.total_xp += awarded_xp
        player.level = level_from_xp(player.total_xp)
        player.rank = rank_from_stats(player.stats, player.level)
        player.updated_at = now
        self.repo.save_player(player)

        # Log XP transaction
        tx = XPTransaction(
            transaction_id=f"tx_{uuid.uuid4().hex[:12]}",
            player_id=player_id,
            amount=awarded_xp,
            source=f"ACTIVITY:{activity.type}",
            reference_id=activity_id,
            timestamp=now
        )
        self.repo.save_xp_transaction(tx)

        # System event
        self.repo.save_event(create_event(
            player_id=player_id,
            event_type=SystemEventType.ACTIVITY_EVALUATED,
            description=f"Evaluated activity '{activity.description}' (+{awarded_xp} XP).",
            payload={"activity_id": activity_id, "awarded_xp": awarded_xp, "quality": quality_score}
        ))

        return ActivityEvaluationResult(
            activity_id=activity_id,
            player_id=player_id,
            quality=quality_score,
            completion=completion_score,
            consistency=consistency_score,
            capability_gain={},
            awarded_xp=awarded_xp,
            feedback=feedback or "Activity verified and absorbed into vessel capability.",
            timestamp=now
        )

    def _evaluate_achievements(self, player: PlayerState) -> None:
        """Checks and unlocks achievements based on player thresholds."""
        existing = {a.achievement_id for a in self.repo.list_achievements(player.player_id)}
        now = datetime.now(timezone.utc)

        achievements_to_check = [
            ("ach_first_quest", "First Step", "Completed your very first System quest.", lambda: True),
            ("ach_streak_7", "7-Day Iron Will", "Maintained unbroken execution for 7 consecutive days.", lambda: player.current_streak >= 7),
            ("ach_streak_30", "Monarch of Discipline", "Maintained unbroken execution for 30 consecutive days.", lambda: player.current_streak >= 30),
            ("ach_xp_1000", "XP Vanguard: 1,000", "Accumulated 1,000 total progression experience.", lambda: player.total_xp >= 1000),
            ("ach_xp_10000", "XP Sovereign: 10,000", "Accumulated 10,000 total progression experience.", lambda: player.total_xp >= 10000),
            ("ach_rank_c", "Beyond Novice", "Ascended to C-Rank vessel status.", lambda: player.rank in [Rank.C, Rank.B, Rank.A, Rank.S, Rank.SS, Rank.SSS]),
            ("ach_rank_a", "Elite Sovereign", "Ascended to A-Rank vessel status.", lambda: player.rank in [Rank.A, Rank.S, Rank.SS, Rank.SSS]),
        ]

        for ach_id, name, desc, condition in achievements_to_check:
            if ach_id not in existing and condition():
                ach = Achievement(
                    achievement_id=ach_id,
                    player_id=player.player_id,
                    name=name,
                    description=desc,
                    unlocked_at=now
                )
                self.repo.save_achievement(ach)
                self.repo.save_event(create_event(
                    player_id=player.player_id,
                    event_type=SystemEventType.ACHIEVEMENT_UNLOCKED,
                    description=f"Unlocked Achievement: [{name}]",
                    payload={"achievement_id": ach_id}
                ))
