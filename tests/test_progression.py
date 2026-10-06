"""
Unit tests for progression, deterministic XP, and rank calculations.
"""

import pytest
from vessel_system.progression import (
    xp_required_for_level, level_from_xp, calculate_activity_xp,
    rank_from_stats, DIFFICULTY_MULTIPLIERS
)
from vessel_system.models import Rank, Stats


def test_level_xp_math():
    assert xp_required_for_level(1) == 0
    assert xp_required_for_level(2) == 100
    assert xp_required_for_level(3) > xp_required_for_level(2)

    # Invert level calculation
    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(500) >= 3


def test_activity_xp_multipliers():
    base_e = calculate_activity_xp(duration_minutes=60, difficulty=Rank.E)
    base_s = calculate_activity_xp(duration_minutes=60, difficulty=Rank.S)
    base_sss = calculate_activity_xp(duration_minutes=60, difficulty=Rank.SSS)

    assert base_s > base_e
    assert base_sss > base_s
    assert DIFFICULTY_MULTIPLIERS[Rank.S] == 2.0


def test_rank_from_stats():
    # Base stats (all 10.0, level 1) -> E
    base_stats = Stats()
    assert rank_from_stats(base_stats, level=1) == Rank.E

    # Elevated stats but low level -> Cannot be high rank
    mid_stats = Stats(
        STR=30, AGI=30, VIT=30, INT=30, PER=30,
        WIL=30, DISC=30, KNOW=30, TECH=30, RES=30, ADP=30
    )
    assert rank_from_stats(mid_stats, level=2) == Rank.D  # C requires level 10

    # With level 12 -> C rank
    assert rank_from_stats(mid_stats, level=12) == Rank.C

    # High rank evaluation
    high_stats = Stats(
        STR=70, AGI=70, VIT=70, INT=70, PER=70,
        WIL=70, DISC=70, KNOW=70, TECH=70, RES=70, ADP=70
    )
    assert rank_from_stats(high_stats, level=45) == Rank.S
