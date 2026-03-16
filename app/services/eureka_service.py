from typing import List, Optional
from app.models.events import NormalizedEvent


POSITIVE_SIGNALS = {
    "identified root cause": 5,
    "root cause": 4,
    "issue caused by": 4,
    "fix is": 4,
    "rolled back": 4,
    "restart": 3,
    "restarted": 3,
    "certificate expired": 5,
    "misconfigured": 4,
    "restored traffic": 5,
    "stabilized service": 5,
    "memory leak": 5,
    "connection pool exhausted": 5,
}

NEGATIVE_SIGNALS = {
    "maybe": -3,
    "possibly": -3,
    "trying": -2,
    "testing": -2,
    "investigating": -1,
}


class EurekaService:
    def detect_eureka_event(self, timeline_events: List[NormalizedEvent]) -> Optional[NormalizedEvent]:
        best_event = None
        best_score = 0

        for event in timeline_events:
            if event.source not in {"work_note", "comment"}:
                continue

            text = event.content.lower()
            score = 0

            for phrase, value in POSITIVE_SIGNALS.items():
                if phrase in text:
                    score += value

            for phrase, value in NEGATIVE_SIGNALS.items():
                if phrase in text:
                    score += value

            if event.label == "FIX_DISCOVERY":
                score += 3
            elif event.label == "MITIGATION":
                score += 2
            elif event.label == "RESOLUTION":
                score += 2

            if score > best_score:
                best_score = score
                best_event = event

        return best_event