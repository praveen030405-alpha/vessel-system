"""
Unit tests for WeakestLinkAnalyzer.
Verifies multi-factor weakness diagnosis (low stats, failure patterns, activity neglect).
"""

from vessel_system.weakest_link import WeakestLinkAnalyzer
from vessel_system.models import PlayerState, Stats, Quest, Activity, QuestStatus, Rank


def test_weakest_link_lowest_stat():
    player = PlayerState(
        player_id="test",
        stats=Stats(
            STR=25.0, AGI=25.0, VIT=25.0, INT=25.0, PER=25.0,
            WIL=25.0, DISC=25.0, KNOW=25.0, TECH=5.0, RES=25.0, ADP=25.0
        )
    )
    analysis = WeakestLinkAnalyzer.analyze(player)
    assert analysis.weakest_stat == "TECH"
    assert "TECH" in analysis.reason


def test_weakest_link_failed_quest_adaptation():
    # If stats are equal, but a quest targeting DISC failed, DISC should be prioritized
    player = PlayerState(
        player_id="test",
        stats=Stats()  # all 10.0
    )
    failed_quest = Quest(
        quest_id="q_fail",
        player_id="test",
        type="DAILY",
        title="Protocol Zero",
        description="Deep work drill",
        difficulty=Rank.E,
        status=QuestStatus.FAILED,
        stat_targets={"DISC": 0.5}
    )

    analysis = WeakestLinkAnalyzer.analyze(player, recent_quests=[failed_quest])
    assert analysis.weakest_stat == "DISC"
    assert "Recent failure" in analysis.reason
