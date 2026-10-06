"""
Deterministic XP, Level, and Rank Progression Engine.
Provides non-linear mathematical progression rules, difficulty multipliers, and rank evaluation.
"""

import math
from typing import Dict, Tuple
from vessel_system.models import Rank, Stats

# Configurable difficulty multipliers
DIFFICULTY_MULTIPLIERS: Dict[Rank, float] = {
    Rank.E: 0.75,
    Rank.D: 0.90,
    Rank.C: 1.00,
    Rank.B: 1.25,
    Rank.A: 1.60,
    Rank.S: 2.00,
    Rank.SS: 2.50,
    Rank.SSS: 3.25,
}

# Base XP parameters for non-linear curve:
# Cumulative XP to reach level L:
# Total XP(L) = round(100 * ((L - 1) ** 1.8))
BASE_LEVEL_XP_SCALE = 100.0
XP_EXPONENT = 1.8


def xp_required_for_level(level: int) -> int:
    """
    Returns the total cumulative XP required to reach a specific level.
    Level 1 requires 0 XP.
    """
    if level <= 1:
        return 0
    return int(round(BASE_LEVEL_XP_SCALE * ((level - 1) ** XP_EXPONENT)))


def xp_for_next_level(current_level: int) -> int:
    """
    Returns delta XP needed to move from current_level to current_level + 1.
    """
    return xp_required_for_level(current_level + 1) - xp_required_for_level(current_level)


def level_from_xp(total_xp: int) -> int:
    """
    Determines level deterministically from cumulative total XP.
    Inverts the non-linear XP curve: Level = 1 + floor((total_xp / 100) ** (1 / 1.8))
    """
    if total_xp <= 0:
        return 1
    raw = (total_xp / BASE_LEVEL_XP_SCALE) ** (1.0 / XP_EXPONENT)
    return int(math.floor(raw)) + 1


def calculate_activity_xp(
    duration_minutes: int,
    difficulty: Rank,
    quality_score: float = 1.0,
    completion_score: float = 1.0
) -> int:
    """
    Calculates deterministic XP for an activity.
    Activity XP = Base (duration * 2) * Difficulty Multiplier * Quality * Completion.
    Capped at realistic bounds.
    """
    safe_duration = max(1, min(duration_minutes, 480))  # Max 8 hours per single activity
    safe_quality = max(0.1, min(quality_score, 1.0))
    safe_completion = max(0.1, min(completion_score, 1.0))

    base_xp = safe_duration * 2.0  # e.g., 30 mins = 60 base XP
    multiplier = DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)

    calculated = base_xp * multiplier * safe_quality * safe_completion
    return max(5, int(round(calculated)))


def rank_from_stats(stats: Stats, level: int) -> Rank:
    """
    Evaluates player Rank deterministically based on:
    1. Average attribute power
    2. Minimum attribute threshold (no hyper-specialized E-rank glass cannons get S-rank)
    3. Player level requirement
    """
    stat_dict = stats.to_dict()
    stat_values = list(stat_dict.values())
    avg_stat = sum(stat_values) / len(stat_values)
    min_stat = min(stat_values)

    # Threshold checks from highest to lowest
    if avg_stat >= 100.0 and min_stat >= 60.0 and level >= 75:
        return Rank.SSS
    if avg_stat >= 80.0 and min_stat >= 48.0 and level >= 55:
        return Rank.SS
    if avg_stat >= 65.0 and min_stat >= 38.0 and level >= 40:
        return Rank.S
    if avg_stat >= 50.0 and min_stat >= 28.0 and level >= 28:
        return Rank.A
    if avg_stat >= 38.0 and min_stat >= 20.0 and level >= 18:
        return Rank.B
    if avg_stat >= 26.0 and min_stat >= 14.0 and level >= 10:
        return Rank.C
    if avg_stat >= 16.0 and min_stat >= 11.0 and level >= 2:
        return Rank.D
    return Rank.E
