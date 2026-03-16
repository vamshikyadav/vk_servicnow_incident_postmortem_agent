from datetime import datetime
from typing import List, Optional
from app.models.events import NormalizedEvent
from app.models.incident import IncidentRecord


DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
]


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


class TimelineService:
    def build_timeline(self, audit_events: List[NormalizedEvent], note_events: List[NormalizedEvent]) -> List[NormalizedEvent]:
        all_events = audit_events + note_events
        return sorted(all_events, key=lambda e: e.timestamp)

    def calculate_mttr_minutes(self, incident: IncidentRecord) -> Optional[int]:
        opened = parse_dt(incident.opened_at)
        resolved = parse_dt(incident.resolved_at)

        if not opened or not resolved:
            return None

        delta = resolved - opened
        return int(delta.total_seconds() // 60)