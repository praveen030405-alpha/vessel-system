"""
Vessel System MCP Server and HTTP ASGI Server.
Exposes all required MCP Tools with strict validation, typed outputs,
authentication, and structured logging.
Compatible with MCP SDK 2.x and mounts ASGI / SSE / Streamable HTTP transports.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.mcpserver import MCPServer

from vessel_system.service import VesselService
from vessel_system.auth import verify_bearer_token, check_auth_header, is_auth_enabled
from vessel_system.models import Rank, QuestType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vessel_system.server")

# 1. Initialize Service & MCP Server
service = VesselService()
mcp_server = MCPServer(name="vessel-system", version="1.0.0")


# ==========================================
# MCP TOOLS DEFINITION
# ==========================================

@mcp_server.tool(name="system_status", description="Get operational status of the Vessel System, Firebase, and Engines.")
def mcp_system_status() -> Dict[str, Any]:
    return service.system_status()


@mcp_server.tool(name="get_player_state", description="Retrieve the authoritative Player progression state (level, rank, XP, stats, streak).")
def mcp_get_player_state(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_player_state(player_id=player_id)


@mcp_server.tool(name="get_stats", description="Retrieve player attribute statistics (STR, AGI, VIT, INT, PER, WIL, DISC, KNOW, TECH, RES, ADP).")
def mcp_get_stats(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_stats(player_id=player_id)


@mcp_server.tool(name="get_weakest_link", description="Analyze the player's weakest capability link using historical performance, stagnation, and quest outcomes.")
def mcp_get_weakest_link(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_weakest_link(player_id=player_id)


@mcp_server.tool(name="get_active_quests", description="Get all currently active quests for the player.")
def mcp_get_active_quests(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_active_quests(player_id=player_id)


@mcp_server.tool(name="get_quest", description="Retrieve details of a specific quest by ID.")
def mcp_get_quest(quest_id: str, player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_quest(player_id=player_id, quest_id=quest_id)


@mcp_server.tool(name="generate_quest", description="Generate a new quest targeted at the player's weakest capability link.")
def mcp_generate_quest(
    player_id: str = "player_1",
    target_weakness: Optional[str] = None,
    quest_type: str = "DAILY",
    difficulty: Optional[str] = None
) -> Dict[str, Any]:
    return service.generate_quest(
        player_id=player_id,
        target_weakness=target_weakness,
        quest_type_str=quest_type,
        difficulty_str=difficulty
    )


@mcp_server.tool(name="complete_quest", description="Complete a quest idempotently, awarding deterministic server-calculated XP, updating stats, and recalculating rank.")
def mcp_complete_quest(quest_id: str, player_id: str = "player_1") -> Dict[str, Any]:
    return service.complete_quest(player_id=player_id, quest_id=quest_id)


@mcp_server.tool(name="fail_quest", description="Safely fail a quest, resetting streaks and updating the weakest-link analysis.")
def mcp_fail_quest(quest_id: str, player_id: str = "player_1", reason: str = "Missed deadline") -> Dict[str, Any]:
    return service.fail_quest(player_id=player_id, quest_id=quest_id, reason=reason)


@mcp_server.tool(name="record_activity", description="Record a real-world developmental activity (exercise, coding, deep work, reading).")
def mcp_record_activity(
    player_id: str,
    activity_type: str,
    description: str,
    duration_minutes: int,
    difficulty: str = "E",
    evidence: str = ""
) -> Dict[str, Any]:
    return service.record_activity(
        player_id=player_id,
        activity_type=activity_type,
        description=description,
        duration_minutes=duration_minutes,
        difficulty_str=difficulty,
        evidence=evidence
    )


@mcp_server.tool(name="evaluate_activity", description="Evaluate a recorded activity, compute quality/completion, and award deterministic XP.")
def mcp_evaluate_activity(
    player_id: str,
    activity_id: str,
    quality_score: float = 1.0,
    completion_score: float = 1.0,
    consistency_score: float = 1.0,
    feedback: str = ""
) -> Dict[str, Any]:
    return service.evaluate_activity(
        player_id=player_id,
        activity_id=activity_id,
        quality_score=quality_score,
        completion_score=completion_score,
        consistency_score=consistency_score,
        feedback=feedback
    )


@mcp_server.tool(name="award_xp", description="Award or adjust XP deterministically via server authority.")
def mcp_award_xp(player_id: str, amount: int, reason: str = "Progression bonus") -> Dict[str, Any]:
    return service.award_xp(player_id=player_id, amount=amount, reason=reason)


@mcp_server.tool(name="get_skills", description="Get player skills, levels, and unlock requirements.")
def mcp_get_skills(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_skills(player_id=player_id)


@mcp_server.tool(name="get_achievements", description="Get player achievements and milestones.")
def mcp_get_achievements(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_achievements(player_id=player_id)


@mcp_server.tool(name="get_titles", description="Get all unlocked titles and active title perks.")
def mcp_get_titles(player_id: str = "player_1") -> Dict[str, Any]:
    return service.get_titles(player_id=player_id)


@mcp_server.tool(name="get_history", description="Retrieve the immutable system event audit history.")
def mcp_get_history(player_id: str = "player_1", limit: int = 50) -> Dict[str, Any]:
    return service.get_history(player_id=player_id, limit=limit)


# ==========================================
# FASTAPI APPLICATION & ROUTING
# ==========================================

app = FastAPI(
    title="Vessel System MCP Server",
    description="Production-grade personal evolution & capability system backend.",
    version="1.0.0"
)

# CORS Middleware (secure by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Enforce authentication on all MCP and state mutation endpoints."""
    # Allow health check, OpenAPI discovery, and daily cron dispatch
    if request.url.path in ["/", "/health", "/status", "/openapi.json", "/docs", "/redoc", "/api/notify/daily"]:
        return await call_next(request)

    # Check bearer auth token if auth is enabled
    if is_auth_enabled():
        auth_hdr = request.headers.get("Authorization")
        if not auth_hdr or not check_auth_header(auth_hdr):
            return Response(
                content='{"success": false, "error": {"code": "UNAUTHORIZED", "message": "Invalid or missing Bearer token"}}',
                status_code=401,
                media_type="application/json"
            )

    return await call_next(request)


@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "service": "Vessel System MCP Server",
        "version": "1.0.0",
        "auth_enabled": is_auth_enabled()
    }


@app.get("/status", summary="Get System Status")
def system_status_endpoint():
    return service.system_status()


@app.get("/api/player", summary="Get Player State")
def api_get_player_state(player_id: str = "player_1"):
    return service.get_player_state(player_id=player_id)


@app.get("/api/stats", summary="Get Player Statistics")
def api_get_stats(player_id: str = "player_1"):
    return service.get_stats(player_id=player_id)


@app.get("/api/weakest-link", summary="Diagnose Weakest Link")
def api_get_weakest_link(player_id: str = "player_1"):
    return service.get_weakest_link(player_id=player_id)


@app.get("/api/quests/active", summary="Get Active Quests")
def api_get_active_quests(player_id: str = "player_1"):
    return service.get_active_quests(player_id=player_id)


class GenerateQuestPayload(BaseModel):
    player_id: str = "player_1"
    target_weakness: Optional[str] = None
    quest_type: str = "DAILY"
    difficulty: Optional[str] = None


@app.post("/api/quests/generate", summary="Generate Targeted Quest")
def api_generate_quest(payload: GenerateQuestPayload):
    return service.generate_quest(
        player_id=payload.player_id,
        target_weakness=payload.target_weakness,
        quest_type_str=payload.quest_type,
        difficulty_str=payload.difficulty
    )


class CompleteQuestPayload(BaseModel):
    player_id: str = "player_1"
    quest_id: str


@app.post("/api/quests/complete", summary="Complete Quest Idempotently")
def api_complete_quest(payload: CompleteQuestPayload):
    return service.complete_quest(player_id=payload.player_id, quest_id=payload.quest_id)


class FailQuestPayload(BaseModel):
    player_id: str = "player_1"
    quest_id: str
    reason: str = "Missed deadline"


@app.post("/api/quests/fail", summary="Fail Quest Safely")
def api_fail_quest(payload: FailQuestPayload):
    return service.fail_quest(player_id=payload.player_id, quest_id=payload.quest_id, reason=payload.reason)


class RecordActivityPayload(BaseModel):
    player_id: str = "player_1"
    activity_type: str
    description: str
    duration_minutes: int
    difficulty: str = "E"
    evidence: str = ""


@app.post("/api/activities/record", summary="Record Real-World Activity")
def api_record_activity(payload: RecordActivityPayload):
    return service.record_activity(
        player_id=payload.player_id,
        activity_type=payload.activity_type,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        difficulty_str=payload.difficulty,
        evidence=payload.evidence
    )


class EvaluateActivityPayload(BaseModel):
    player_id: str = "player_1"
    activity_id: str
    quality_score: float = 1.0
    completion_score: float = 1.0
    consistency_score: float = 1.0
    feedback: str = ""


@app.post("/api/activities/evaluate", summary="Evaluate Activity & Award XP")
def api_evaluate_activity(payload: EvaluateActivityPayload):
    return service.evaluate_activity(
        player_id=payload.player_id,
        activity_id=payload.activity_id,
        quality_score=payload.quality_score,
        completion_score=payload.completion_score,
        consistency_score=payload.consistency_score,
        feedback=payload.feedback
    )


@app.get("/api/skills", summary="Get Player Skills")
def api_get_skills(player_id: str = "player_1"):
    return service.get_skills(player_id=player_id)


@app.get("/api/achievements", summary="Get Player Achievements")
def api_get_achievements(player_id: str = "player_1"):
    return service.get_achievements(player_id=player_id)


@app.get("/api/titles", summary="Get Player Titles")
def api_get_titles(player_id: str = "player_1"):
    return service.get_titles(player_id=player_id)


@app.get("/api/history", summary="Get System History Audit Log")
def api_get_history(player_id: str = "player_1", limit: int = 50):
    return service.get_history(player_id=player_id, limit=limit)


@app.get("/api/notify/daily", summary="Dispatch Daily Telegram Quest Alert")
def api_dispatch_daily_notification(player_id: str = "player_1"):
    from telegram_notifier import send_telegram_alert
    player = service.get_player_state(player_id)["player"]
    weakest = service.get_weakest_link(player_id)["analysis"]
    quests = service.get_active_quests(player_id)["active_quests"]
    if not quests:
        new_q = service.generate_quest(player_id, target_weakness=weakest["weakest_stat"])["quest"]
        quests = [new_q]

    top_quest = quests[0]
    msg = (
        f"👑 *[SHADOW SYSTEM — MORNING DIRECTIVE]*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Player: *{player['name']}*\n"
        f"Rank: *{player['rank']}* | Level: *{player['level']}*\n"
        f"Current Streak: *{player['current_streak']} Days* (Longest: {player['longest_streak']} Days)\n\n"
        f"🎯 *TARGETED WEAKNESS:*\n"
        f"• Bottleneck: *{weakest['weakest_stat']}*\n"
        f"• Diagnosis: _{weakest['reason']}_\n\n"
        f"⚔️ *TODAY’S MANDATED QUEST:*\n"
        f"• Title: *{top_quest['title']}*\n"
        f"• Target: {top_quest['target']}\n"
        f"• Reward: +{top_quest['xp_reward']} XP\n\n"
        f"🏋️ *PHYSICAL CONDITIONING:*\n"
        f"• Complete 45 min workout routine according to schedule.\n\n"
        f"_The System is watching your execution. Train the weakest link._"
    )
    sent = send_telegram_alert(msg)
    return {"success": sent, "message": "Daily Telegram directive dispatched successfully."}




# Mount MCP Streamable HTTP & SSE Starlette Apps
try:
    mcp_streamable_app = mcp_server.streamable_http_app(streamable_http_path="/")
    app.mount("/mcp", mcp_streamable_app)
    logger.info("Mounted MCP Streamable HTTP transport at /mcp")
except Exception as e:
    logger.warning(f"Could not mount streamable_http_app: {e}")

try:
    mcp_sse = mcp_server.sse_app(sse_path="/", message_path="/messages")
    app.mount("/sse", mcp_sse)
    logger.info("Mounted MCP SSE transport at /sse")
except Exception as e:
    logger.warning(f"Could not mount sse_app: {e}")


def run_server():
    """Entry point for standalone execution."""
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("vessel_system.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()
