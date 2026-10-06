"""
Event dispatcher and progression event factory.
Creates immutable audit trail for all key state mutations.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from vessel_system.models import SystemEvent, SystemEventType


def create_event(
    player_id: str,
    event_type: SystemEventType,
    description: str,
    payload: Dict[str, Any] = None
) -> SystemEvent:
    """Creates a strongly typed SystemEvent."""
    return SystemEvent(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        player_id=player_id,
        event_type=event_type,
        description=description,
        payload=payload or {},
        timestamp=datetime.now(timezone.utc),
    )
