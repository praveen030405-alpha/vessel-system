"""
Unit tests for VesselRepository, Activities, and Full Event Audit Log.
"""

import pytest
from vessel_system.engine import VesselEngine
from vessel_system.repository import InMemoryRepository
from vessel_system.models import Rank, QuestStatus


@pytest.fixture
def test_engine():
    repo = InMemoryRepository()
    return VesselEngine(repository=repo)


def test_activity_recording_and_evaluation(test_engine):
    player, _ = test_engine.get_or_initialize_player("p_act", "Tester")
    init_xp = player.total_xp

    # Record 45 min coding session
    act = test_engine.record_activity(
        player_id="p_act",
        activity_type="TECH",
        description="Refactored database layer",
        duration_minutes=45,
        difficulty=Rank.C,
        evidence="git commit sha 123"
    )
    assert act.activity_id.startswith("act_")
    assert act.duration_minutes == 45

    # Evaluate activity
    eval_res = test_engine.evaluate_activity(
        player_id="p_act",
        activity_id=act.activity_id,
        quality_score=0.9,
        completion_score=1.0,
        consistency_score=1.0,
        feedback="Flawless architectural implementation"
    )

    assert eval_res.awarded_xp > 0
    updated_player = test_engine.get_player_state("p_act")
    assert updated_player.total_xp == init_xp + eval_res.awarded_xp


def test_event_audit_trail(test_engine):
    player, _ = test_engine.get_or_initialize_player("p_evt", "Auditor")
    events = test_engine.repo.list_events("p_evt")
    assert len(events) >= 1
    assert any(e.event_type.value == "PLAYER_INITIALIZED" for e in events)

    # Generate quest logs an event
    quest = test_engine.generate_quest("p_evt")
    events_after = test_engine.repo.list_events("p_evt")
    assert any(e.event_type.value == "QUEST_CREATED" for e in events_after)
