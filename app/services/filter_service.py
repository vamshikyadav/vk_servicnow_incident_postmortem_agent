from typing import List
from app.models.events import NormalizedEvent


KNOWN_BOT_USERS = {
    "system",
    "servicenow",
    "monitoring_bot",
    "integration_user",
}

AUTOMATION_PATTERNS = [
    "monitoring alert triggered",
    "assignment rule applied",
    "sla updated",
    "state changed automatically",
    "notification sent",
    "auto-resolved",
]

STRONG_HUMAN_SIGNALS = [
    "found",
    "identified",
    "root cause",
    "fixed",
    "rolled back",
    "restarted",
    "mitigated",
    "recovered",
    "observed",
    "checked logs",
    "investigating",
]


class FilterService:
    def classify_and_filter(self, events: List[NormalizedEvent]) -> List[NormalizedEvent]:
        filtered: List[NormalizedEvent] = []

        for event in events:
            lowered = event.content.lower().strip()
            author = (event.author or "").lower().strip()

            if author in KNOWN_BOT_USERS:
                event.label = "AUTOMATION_NOISE"
                continue

            if any(p in lowered for p in AUTOMATION_PATTERNS):
                event.label = "AUTOMATION_NOISE"
                continue

            if len(lowered) < 8:
                event.label = "AUTOMATION_NOISE"
                continue

            if any(sig in lowered for sig in STRONG_HUMAN_SIGNALS):
                if "root cause" in lowered or "identified" in lowered:
                    event.label = "FIX_DISCOVERY"
                elif "mitigated" in lowered or "restarted" in lowered or "rolled back" in lowered:
                    event.label = "MITIGATION"
                elif "fixed" in lowered or "recovered" in lowered:
                    event.label = "RESOLUTION"
                else:
                    event.label = "HUMAN_INVESTIGATION"
            else:
                event.label = "STATUS_UPDATE"

            filtered.append(event)

        return filtered