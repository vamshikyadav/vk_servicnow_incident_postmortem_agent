from pydantic import BaseModel
from typing import List, Optional


class Metrics(BaseModel):
    mttr_minutes: Optional[int] = None
    time_to_detect_minutes: Optional[int] = None
    time_to_mitigate_minutes: Optional[int] = None
    eureka_timestamp: Optional[str] = None


class QualityChecks(BaseModel):
    has_ci: bool = False
    resolution_note_score: int = 0
    has_clear_root_cause: bool = False
    has_action_items: bool = False


class PostmortemDraft(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    impact: Optional[str] = None
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    timeline_markdown: Optional[str] = None
    action_items: List[str] = []