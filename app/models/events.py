from pydantic import BaseModel
from typing import Optional, Literal, List


EventSource = Literal["incident", "audit", "work_note", "comment"]
EventType = Literal[
    "STATE_CHANGE",
    "ASSIGNMENT_CHANGE",
    "PRIORITY_CHANGE",
    "CI_UPDATE",
    "WORK_NOTE",
    "COMMENT",
    "RESOLUTION",
    "OTHER",
]

EventLabel = Literal[
    "HUMAN_INVESTIGATION",
    "AUTOMATION_NOISE",
    "STATUS_UPDATE",
    "FIX_DISCOVERY",
    "MITIGATION",
    "RESOLUTION",
    "FOLLOW_UP",
    "UNKNOWN",
]


class NormalizedEvent(BaseModel):
    timestamp: str
    source: EventSource
    event_type: EventType
    author: Optional[str] = None
    author_type: Optional[str] = None  # human, bot, integration, unknown
    content: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    label: EventLabel = "UNKNOWN"
    confidence: float = 1.0


class IncidentPackage(BaseModel):
    incident: "IncidentRecord"
    audit_events: List[NormalizedEvent]
    work_notes: List[NormalizedEvent]
    comments: List[NormalizedEvent]
    timeline_events: List[NormalizedEvent] = []