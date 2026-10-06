"""
Weakest-Link Engine.
Evaluates Player capability, recent activities, failed quests, and progression stagnation
to identify the user's primary development bottleneck and prescribe targeted growth quests.
"""

from typing import Dict, List, Optional, Tuple
from vessel_system.models import PlayerState, Quest, Activity, QuestStatus


class WeakestLinkAnalysis:
    def __init__(
        self,
        weakest_stat: str,
        weakest_stat_value: float,
        reason: str,
        recommended_quest_type: str,
        diagnosis_details: Dict[str, any]
    ):
        self.weakest_stat = weakest_stat
        self.weakest_stat_value = weakest_stat_value
        self.reason = reason
        self.recommended_quest_type = recommended_quest_type
        self.diagnosis_details = diagnosis_details

    def to_dict(self) -> Dict[str, any]:
        return {
            "weakest_stat": self.weakest_stat,
            "stat_value": self.weakest_stat_value,
            "reason": self.reason,
            "recommended_quest_type": self.recommended_quest_type,
            "diagnosis_details": self.diagnosis_details,
        }


class WeakestLinkAnalyzer:
    """
    Analyzes player state dynamically without relying purely on the lowest numerical stat.
    Weighs:
    - Base stat levels
    - Recent failed quests targeting specific stats
    - Activity deficit (which capabilities haven't been exercised in recent days)
    - Stagnation duration
    """

    STAT_CATEGORIES: Dict[str, str] = {
        "STR": "Physical Strength & Power",
        "AGI": "Agility & Speed",
        "VIT": "Endurance, Recovery & Health",
        "INT": "Intellectual & Cognitive Architecture",
        "PER": "Perception & Environmental Attention",
        "WIL": "Willpower & Emotional Regulation",
        "DISC": "Discipline, Habit Formation & Consistency",
        "KNOW": "Domain Breadth & Knowledge Acquisition",
        "TECH": "Technical Craft & Engineering Execution",
        "RES": "Stress Resilience & Hardship Tolerance",
        "ADP": "Adaptability Under Uncertainty",
    }

    @classmethod
    def analyze(
        cls,
        player: PlayerState,
        recent_quests: Optional[List[Quest]] = None,
        recent_activities: Optional[List[Activity]] = None
    ) -> WeakestLinkAnalysis:
        stats_dict = player.stats.to_dict()
        recent_quests = recent_quests or []
        recent_activities = recent_activities or []

        # 1. Base penalty scores per stat (lower stat = higher vulnerability)
        # Average score baseline
        avg_stat = sum(stats_dict.values()) / max(1, len(stats_dict))
        vulnerability_scores: Dict[str, float] = {}

        for stat, val in stats_dict.items():
            # Distance below average
            deficit = max(0.0, avg_stat - val) * 2.0
            # Base absolute value weight (100 / value)
            raw_vulnerability = (100.0 / max(1.0, val)) + deficit
            vulnerability_scores[stat] = raw_vulnerability

        # 2. Factor in failed quests: increase vulnerability of failed stat targets
        failed_count_by_stat: Dict[str, int] = {k: 0 for k in stats_dict}
        for q in recent_quests:
            if q.status == QuestStatus.FAILED:
                for stat_target in q.stat_targets.keys():
                    if stat_target in vulnerability_scores:
                        vulnerability_scores[stat_target] += 15.0
                        failed_count_by_stat[stat_target] += 1

        # 3. Factor in activity deficit (neglect penalty)
        trained_stats_recent: Dict[str, int] = {k: 0 for k in stats_dict}
        for act in recent_activities:
            act_type = act.type.upper()
            for stat in stats_dict:
                if stat in act_type or stat in act.description.upper():
                    trained_stats_recent[stat] += 1

        for stat, count in trained_stats_recent.items():
            if count == 0:
                # Neglected capability
                vulnerability_scores[stat] += 8.0

        # 4. Find the stat with the highest vulnerability score
        weakest_stat = max(vulnerability_scores, key=lambda k: vulnerability_scores[k])
        weakest_val = stats_dict[weakest_stat]

        # Formulate reason and diagnosis
        reasons = []
        if failed_count_by_stat[weakest_stat] > 0:
            reasons.append(f"Recent failure in {failed_count_by_stat[weakest_stat]} objective(s) targeting {weakest_stat}.")
        if trained_stats_recent[weakest_stat] == 0:
            reasons.append(f"Observed training deficit: {weakest_stat} has not been stimulated in recent activities.")
        if weakest_val <= min(stats_dict.values()):
            reasons.append(f"Stat value ({weakest_val:.1f}) is at or near the absolute floor of your vessel.")

        if not reasons:
            reasons.append(f"{weakest_stat} ({cls.STAT_CATEGORIES.get(weakest_stat, weakest_stat)}) is lagging the average vessel capability.")

        diagnosis = {
            "vulnerability_scores": {k: round(v, 2) for k, v in vulnerability_scores.items()},
            "stat_values": {k: round(v, 2) for k, v in stats_dict.items()},
            "average_stat": round(avg_stat, 2),
            "recent_fails": failed_count_by_stat,
            "recent_activity_count": len(recent_activities),
        }

        # Determine recommended quest classification
        stat_to_quest_category = {
            "STR": "PHYSICAL_TRAINING",
            "AGI": "MOBILITY_AND_SPEED",
            "VIT": "CARDIO_AND_RECOVERY",
            "INT": "DEEP_COGNITION",
            "PER": "ATTENTION_AND_ANALYSIS",
            "WIL": "WILLPOWER_ENDURANCE",
            "DISC": "EXECUTION_CONSISTENCY",
            "KNOW": "DOMAIN_RESEARCH",
            "TECH": "TECHNICAL_IMPLEMENTATION",
            "RES": "STRESS_TOLERANCE",
            "ADP": "UNCONVENTIONAL_PROBLEM",
        }
        rec_type = stat_to_quest_category.get(weakest_stat, "BALANCED_DEVELOPMENT")

        return WeakestLinkAnalysis(
            weakest_stat=weakest_stat,
            weakest_stat_value=weakest_val,
            reason=" ".join(reasons),
            recommended_quest_type=rec_type,
            diagnosis_details=diagnosis
        )
