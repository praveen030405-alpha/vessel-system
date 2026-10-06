"""
Telegram Notification Dispatcher for the Shadow System.
Sends rich status alerts, daily quest briefings, and workout routines.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8862451361:AAHBTbnq5NwY--6NETQc2eMcCwjeONEwBLg")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1538199820")


def send_telegram_alert(message: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(CHAT_ID),
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        data = res.json()
        if data.get("ok"):
            print("Telegram alert sent successfully!")
            return True
        else:
            print("Telegram API error:", data)
            return False
    except Exception as e:
        print("Failed to dispatch alert:", e)
        return False


if __name__ == "__main__":
    welcome_msg = (
        "👑 *[SHADOW SYSTEM ONLINE]*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Greetings, Player *Praveen*.\n"
        "The System has acknowledged your vessel.\n\n"
        "*VESSEL STATUS MATRIX:*\n"
        "• Rank: *E*\n"
        "• Level: *1*\n"
        "• Total XP: *52*\n"
        "• Current Streak: *1 Day* (Longest: 1 Day)\n"
        "• Active Title: *The Initiate*\n\n"
        "*ATTRIBUTES:*\n"
        "• STR: *10.45*  |  VIT: *10.22*\n"
        "• DISC: *10.00* |  TECH: *10.00*\n"
        "• INT: *10.00*  |  WIL: *10.00*\n\n"
        "*TODAY’S MANDATORY DIRECTIVE:*\n"
        "Objective: Complete 45 min core physical conditioning.\n"
        "Reward: +52 XP | +0.45 STR\n\n"
        "_The System will notify you daily. Train your weakest link._"
    )
    send_telegram_alert(welcome_msg)
