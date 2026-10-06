"""
Interactive Vessel System CLI Tester.
Allows human operators to interact with the local Vessel System as the Player,
simulating ChatGPT orchestrator tool calls directly against the live Firestore database.
"""

import sys
from vessel_system.service import VesselService
from vessel_system.models import Rank, QuestType


def main():
    service = VesselService()
    player_id = "player_1"

    print("=" * 60)
    print("        VESSEL SYSTEM — INTERACTIVE COMMAND MATRIX")
    print("=" * 60)

    # Initial status check
    stat = service.system_status()
    print(f"Status: {stat['status']}\n")

    while True:
        print("\nSelect Directive / Action:")
        print(" [1] System, show my status. (Matrix, stats, level, rank)")
        print(" [2] System, what is my current weakest link? (Bottleneck diagnosis)")
        print(" [3] System, generate a quest for my weakest stat.")
        print(" [4] System, what are today's active quests?")
        print(" [5] System, I completed the quest.")
        print(" [6] System, evaluate today's work. (Record & evaluate activity)")
        print(" [7] System, initiate a boss quest.")
        print(" [8] System, show my achievements & titles.")
        print(" [9] System, show my history.")
        print(" [0] Exit Vessel Console")

        choice = input("\nEnter Command [0-9]: ").strip()

        if choice == "0":
            print("\nVessel System entering standby. Sovereign progression logged.")
            break

        elif choice == "1":
            p = service.get_player_state(player_id)["player"]
            print("\n" + "=" * 50)
            print(f"PLAYER: {p['name']} | RANK: {p['rank']} | LEVEL: {p['level']}")
            print(f"TOTAL XP: {p['total_xp']} | STREAK: {p['current_streak']} Days (Longest: {p['longest_streak']} Days)")
            print(f"TITLE: {p['active_title']}")
            print("-" * 50)
            print("ATTRIBUTES:")
            for k, v in p["stats"].items():
                print(f"  {k:5}: {v:.2f}")
            print("=" * 50)

        elif choice == "2":
            w = service.get_weakest_link(player_id)["analysis"]
            print("\n" + "=" * 50)
            print("PRIMARY WEAKNESS DIAGNOSIS:")
            print(f"Weakest Link : {w['weakest_stat']} (Floor: {w['stat_value']:.2f})")
            print(f"Diagnosis    : {w['reason']}")
            print(f"Prescription : {w['recommended_quest_type']}")
            print("=" * 50)

        elif choice == "3":
            q = service.generate_quest(player_id)["quest"]
            print("\n" + "=" * 50)
            print(f"NEW DIRECTIVE ISSUED: {q['title']}")
            print(f"Quest ID    : {q['quest_id']}")
            print(f"Difficulty  : Rank {q['difficulty']}")
            print(f"Description : {q['description']}")
            print(f"Target      : {q['target']}")
            print(f"Reward      : +{q['xp_reward']} XP | Targets: {q['stat_targets']}")
            print("=" * 50)

        elif choice == "4":
            quests = service.get_active_quests(player_id)["active_quests"]
            print("\n" + "=" * 50)
            print(f"ACTIVE DIRECTIVES ({len(quests)}):")
            for q in quests:
                print(f" • [{q['quest_id']}] ({q['difficulty']}) {q['title']}")
                print(f"   Objective: {q['target']}")
                print(f"   Reward   : +{q['xp_reward']} XP")
            print("=" * 50)

        elif choice == "5":
            quests = service.get_active_quests(player_id)["active_quests"]
            if not quests:
                print("\n[!] No active quests available. Generate one first.")
                continue
            print("\nSelect Quest to Complete:")
            for i, q in enumerate(quests, 1):
                print(f" [{i}] {q['title']} (ID: {q['quest_id']})")
            q_idx = input("Select number: ").strip()
            try:
                sel_quest = quests[int(q_idx) - 1]
                res = service.complete_quest(player_id, sel_quest["quest_id"])
                print("\n" + "=" * 50)
                print(f"RESULT: {res['message']}")
                print(f"XP Granted: +{res.get('xp_awarded', 0)} XP")
                if res.get("level_up"):
                    print(f"▲ LEVEL UP! {res['old_level']} -> {res['new_level']}")
                if res.get("rank_up"):
                    print(f"▲ RANK ASCENSION! {res['old_rank']} -> {res['new_rank']}")
                print(f"Current Streak: {res.get('current_streak')} Days")
                print("=" * 50)
            except Exception as e:
                print(f"\n[!] Error completing quest: {e}")

        elif choice == "6":
            act_type = input("Activity Category (TECH, DISC, STR, VIT, KNOW, etc.): ").strip().upper() or "TECH"
            desc = input("Activity Description (e.g. built microservice, lifted weights): ").strip() or "Execution session"
            mins = int(input("Duration in minutes (e.g. 45): ").strip() or "45")
            rec = service.record_activity(player_id, act_type, desc, mins)["activity"]
            eval_res = service.evaluate_activity(player_id, rec["activity_id"])["evaluation"]
            print("\n" + "=" * 50)
            print(f"ACTIVITY EVALUATED & ABSORBED:")
            print(f"XP Awarded  : +{eval_res['awarded_xp']} XP")
            print(f"Feedback    : {eval_res['feedback']}")
            print("=" * 50)

        elif choice == "7":
            q = service.generate_quest(player_id, quest_type_str="BOSS")["quest"]
            print("\n" + "=" * 50)
            print(f"⚠️ 72-HOUR BOSS TRIAL COMMENCED: {q['title']}")
            print(f"Target : {q['target']}")
            print(f"Reward : +{q['xp_reward']} XP | Stat Boost: {q['stat_targets']}")
            print("=" * 50)

        elif choice == "8":
            achs = service.get_achievements(player_id)["achievements"]
            titles = service.get_titles(player_id)["titles"]
            print("\n" + "=" * 50)
            print("TITLES:")
            for t in titles:
                print(f" 👑 [{t['name']}]: {t['description']}")
            print("\nACHIEVEMENTS:")
            for a in achs:
                print(f" 🏆 [{a['name']}]: {a['description']}")
            print("=" * 50)

        elif choice == "9":
            events = service.get_history(player_id, limit=10)["events"]
            print("\n" + "=" * 50)
            print(f"RECENT AUDIT LOG ({len(events)} events):")
            for e in events:
                print(f" [{e['timestamp'][:19]}] {e['event_type']}: {e['description']}")
            print("=" * 50)


if __name__ == "__main__":
    main()
