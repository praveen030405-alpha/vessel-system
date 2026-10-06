"""
Unit tests for VesselEngine, Quests, Idempotency, and Failure.
"""

import pytest
from vessel_system.engine import VesselEngine
from vessel_system.repository import InMemoryRepository
from vessel_system.models import Rank, QuestStatus, QuestType


@pytest.fixture
def test_engine():
    repo = InMemoryRepository()
    return VesselEngine(repository=repo)


def test_player_initialization(test_engine):
    player, is_new = test_engine.get_or_initialize_player("p_test", "Shadow")
    assert is_new is True
    assert player.level == 1
    assert player.rank == Rank.E
    assert player.total_xp == 0
    assert player.stats.DISC == 10.0

    # Second call returns existing
    player2, is_new2 = test_engine.get_or_initialize_player("p_test", "Shadow")
    assert is_new2 is False
    assert player2.player_id == player.player_id


def test_quest_generation_and_completion_idempotency(test_engine):
    player, _ = test_engine.get_or_initialize_player("p_test")
    quest = test_engine.generate_quest("p_test", target_weakness="DISC")

    assert quest.status == QuestStatus.ACTIVE
    assert "DISC" in quest.stat_targets

    # First completion awards XP
    initial_xp = player.total_xp
    res1 = test_engine.complete_quest("p_test", quest.quest_id)
    assert res1["success"] is True
    assert res1["xp_awarded"] == quest.xp_reward

    player_after = test_engine.get_player_state("p_test")
    assert player_after.total_xp == initial_xp + quest.xp_reward
    assert player_after.stats.DISC > 10.0

    # Second completion MUST be idempotent and award 0 additional XP
    res2 = test_engine.complete_quest("p_test", quest.quest_id)
    assert res2["success"] is True
    assert res2.get("already_completed") is True
    assert test_engine.get_player_state("p_test").total_xp == player_after.total_xp


def test_quest_failure_resets_streak(test_engine):
    player, _ = test_engine.get_or_initialize_player("p_test")
    player.current_streak = 5
    test_engine.repo.save_player(player)

    quest = test_engine.generate_quest("p_test", target_weakness="TECH")
    res = test_engine.fail_quest("p_test", quest.quest_id, reason="Incomplete milestone")

    assert res["success"] is True
    assert res["streak_reset"] is True
    assert test_engine.get_player_state("p_test").current_streak == 0
