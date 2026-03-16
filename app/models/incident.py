from pydantic import BaseModel, Field
from typing import Optional


class IncidentRecord(BaseModel):
    sys_id: str
    number: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    state: Optional[str] = None
    opened_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    cmdb_ci: Optional[str] = None
    assignment_group: Optional[str] = None
    assigned_to: Optional[str] = None
    business_service: Optional[str] = None
    resolution_notes: Optional[str] = None