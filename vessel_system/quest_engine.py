"""
Quest Generation and Progression Engine.
Provides deterministic, safe, realistic quest generation tailored to weakest links,
quest difficulty progression, and template blueprints.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from vessel_system.models import Quest, QuestType, QuestStatus, Rank, PlayerState
from vessel_system.progression import DIFFICULTY_MULTIPLIERS


QUEST_TEMPLATES = {
    "DISC": [
        {
            "title": "Protocol Zero: Unbroken Deep Work",
            "description": "Engage in 90 minutes of strictly single-tasked high-priority execution with zero external distraction.",
            "target": "90 continuous minutes completed without tab switching or phone interaction",
            "stat_targets": {"DISC": 0.5, "WIL": 0.3},
            "duration_hours": 24,
            "base_xp": 80,
        },
        {
            "title": "Dawn Alignment Protocol",
            "description": "Begin morning routine and core objective on the exact planned minute without hesitation or delay.",
            "target": "Commence core objective at designated schedule without snoozing",
            "stat_targets": {"DISC": 0.4, "RES": 0.2},
            "duration_hours": 24,
            "base_xp": 60,
        }
    ],
    "TECH": [
        {
            "title": "Architecture Forge: Implement Robust Subsystem",
            "description": "Design, implement, and unit-test a clean technical module or refactor a critical bottleneck.",
            "target": "Ship production-grade code with automated test coverage exceeding 90%",
            "stat_targets": {"TECH": 0.6, "INT": 0.4},
            "duration_hours": 48,
            "base_xp": 120,
        },
        {
            "title": "Algorithmic Precision Drill",
            "description": "Solve or implement an intricate algorithmic system from first principles.",
            "target": "Complete algorithmic implementation and verify edge cases",
            "stat_targets": {"TECH": 0.5, "KNOW": 0.3},
            "duration_hours": 24,
            "base_xp": 90,
        }
    ],
    "KNOW": [
        {
            "title": "Synthesis of the Core Text",
            "description": "Deep-read authoritative material in your primary field and produce a concise technical brief of the insights.",
            "target": "Study primary source documentation and extract 3 actionable architectural principles",
            "stat_targets": {"KNOW": 0.7, "INT": 0.3},
            "duration_hours": 24,
            "base_xp": 75,
        }
    ],
    "STR": [
        {
            "title": "Kinetic Overload: Resistance Protocol",
            "description": "Complete a structured, progressive resistance training session focused on compound movements.",
            "target": "Complete resistance workout safely with proper biomechanical form",
            "stat_targets": {"STR": 0.6, "VIT": 0.3},
            "duration_hours": 24,
            "base_xp": 70,
        }
    ],
    "AGI": [
        {
            "title": "Proprioceptive Agility & Coordination",
            "description": "Perform dynamic mobility drills, footwork, and reactive speed work.",
            "target": "30 minutes of dedicated agility and dynamic range drills",
            "stat_targets": {"AGI": 0.6, "VIT": 0.2},
            "duration_hours": 24,
            "base_xp": 65,
        }
    ],
    "VIT": [
        {
            "title": "Cardiovascular Vessel Conditioning",
            "description": "Execute a safe Zone 2 sustained aerobic session or interval sprint routine within safe physiological limits.",
            "target": "45 minutes sustained aerobic conditioning",
            "stat_targets": {"VIT": 0.7, "RES": 0.3},
            "duration_hours": 24,
            "base_xp": 75,
        }
    ],
    "INT": [
        {
            "title": "First Principles Deconstruction",
            "description": "Select an intractable or complex domain problem. Deconstruct it into fundamental axioms and derive a solution.",
            "target": "Produce documented first-principles deconstruction of the chosen problem",
            "stat_targets": {"INT": 0.7, "PER": 0.3},
            "duration_hours": 24,
            "base_xp": 85,
        }
    ],
    "PER": [
        {
            "title": "Perceptual Calibration & Error Audit",
            "description": "Conduct a meticulous audit of current work or operational environments, identifying subtle defects or inefficiencies.",
            "target": "Identify and log 3 hidden inefficiencies or errors across your domain",
            "stat_targets": {"PER": 0.6, "INT": 0.3},
            "duration_hours": 24,
            "base_xp": 60,
        }
    ],
    "WIL": [
        {
            "title": "Volitional Bastion: Friction Confrontation",
            "description": "Directly execute the single task you have avoided the most today, without bargaining.",
            "target": "Execute avoided high-friction task to completion",
            "stat_targets": {"WIL": 0.7, "DISC": 0.4},
            "duration_hours": 24,
            "base_xp": 95,
        }
    ],
    "RES": [
        {
            "title": "Adversity Crucible: High-Pressure Focus",
            "description": "Maintain calm, composed, meticulous execution under demanding conditions or cognitive fatigue.",
            "target": "Deliver sustained output through fatigue without degradation in quality",
            "stat_targets": {"RES": 0.6, "WIL": 0.4},
            "duration_hours": 24,
            "base_xp": 90,
        }
    ],
    "ADP": [
        {
            "title": "Novel Terrain Exploration",
            "description": "Tackle an unfamiliar problem or environment outside your comfort zone and produce a functional outcome.",
            "target": "Achieve a functional milestone in an unfamiliar paradigm or toolset",
            "stat_targets": {"ADP": 0.7, "TECH": 0.3},
            "duration_hours": 36,
            "base_xp": 100,
        }
    ]
}


class QuestEngine:
    @staticmethod
    def generate_targeted_quest(
        player: PlayerState,
        weakest_stat: str,
        quest_type: QuestType = QuestType.DAILY,
        difficulty: Optional[Rank] = None
    ) -> Quest:
        """
        Generates an authoritative, safe quest targeting the user's weakest stat.
        Difficulty matches or challenges the player's rank.
        """
        diff = difficulty or player.rank
        templates = QUEST_TEMPLATES.get(weakest_stat, QUEST_TEMPLATES["DISC"])
        # Deterministic rotation based on level and stat
        template_idx = player.level % len(templates)
        tmpl = templates[template_idx]

        multiplier = DIFFICULTY_MULTIPLIERS.get(diff, 1.0)
        xp_reward = int(round(tmpl["base_xp"] * multiplier))

        now = datetime.now(timezone.utc)
        due = now + timedelta(hours=tmpl["duration_hours"])

        # Scale stat gains slightly with rank difficulty
        scaled_targets = {k: round(v * multiplier, 2) for k, v in tmpl["stat_targets"].items()}

        quest_id = f"quest_{uuid.uuid4().hex[:12]}"

        return Quest(
            quest_id=quest_id,
            player_id=player.player_id,
            type=quest_type,
            title=tmpl["title"],
            description=tmpl["description"],
            difficulty=diff,
            status=QuestStatus.ACTIVE,
            target=tmpl["target"],
            progress=0.0,
            xp_reward=xp_reward,
            stat_targets=scaled_targets,
            created_at=now,
            due_at=due,
            metadata={
                "targeted_weakness": weakest_stat,
                "base_xp": tmpl["base_xp"],
                "multiplier": multiplier,
            }
        )

    @staticmethod
    def generate_boss_quest(player: PlayerState, weakest_stat: str) -> Quest:
        """
        Generates a safe, realistic Boss Quest milestone challenge (e.g. 72-hour major trial).
        """
        now = datetime.now(timezone.utc)
        due = now + timedelta(hours=72)
        diff = Rank.A if player.rank in [Rank.E, Rank.D, Rank.C] else Rank.S
        multiplier = DIFFICULTY_MULTIPLIERS.get(diff, 1.6)

        return Quest(
            quest_id=f"boss_{uuid.uuid4().hex[:12]}",
            player_id=player.player_id,
            type=QuestType.BOSS,
            title=f"Boss Trial: Crucible of the {weakest_stat} Monarch",
            description=(
                f"A comprehensive 72-hour milestone test demanding peak performance in {weakest_stat}. "
                "Execute the complete phase of a major real-world initiative without faltering."
            ),
            difficulty=diff,
            status=QuestStatus.ACTIVE,
            target="Successfully complete and document the multi-stage breakthrough project milestone.",
            progress=0.0,
            xp_reward=int(round(350 * multiplier)),
            stat_targets={weakest_stat: round(1.5 * multiplier, 2), "DISC": 1.0, "RES": 1.0},
            created_at=now,
            due_at=due,
            metadata={"is_boss": True, "boss_stat": weakest_stat}
        )
