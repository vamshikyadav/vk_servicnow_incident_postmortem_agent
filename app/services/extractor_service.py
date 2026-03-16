from typing import List
from app.clients.servicenow_client import ServiceNowClient
from app.models.incident import IncidentRecord
from app.models.events import IncidentPackage, NormalizedEvent


class ExtractorService:
    def __init__(self) -> None:
        self.client = ServiceNowClient()

    def extract_incident_package(self, incident_sys_id: str) -> IncidentPackage:
        incident_raw = self.client.get_incident(incident_sys_id).get("result", [])
        if not incident_raw:
            raise ValueError(f"Incident not found for sys_id={incident_sys_id}")

        incident_obj = incident_raw[0]
        incident = IncidentRecord(
            sys_id=incident_obj.get("sys_id", ""),
            number=incident_obj.get("number", ""),
            short_description=incident_obj.get("short_description"),
            description=incident_obj.get("description"),
            priority=incident_obj.get("priority"),
            severity=incident_obj.get("severity"),
            state=incident_obj.get("state"),
            opened_at=incident_obj.get("opened_at"),
            resolved_at=incident_obj.get("resolved_at"),
            closed_at=incident_obj.get("closed_at"),
            cmdb_ci=self._display_value(incident_obj.get("cmdb_ci")),
            assignment_group=self._display_value(incident_obj.get("assignment_group")),
            assigned_to=self._display_value(incident_obj.get("assigned_to")),
            business_service=self._display_value(incident_obj.get("business_service")),
            resolution_notes=incident_obj.get("close_notes"),
        )

        audit_events = self._normalize_audit(
            self.client.get_audit_events(incident_sys_id).get("result", [])
        )
        work_notes, comments = self._normalize_journal(
            self.client.get_journal_entries(incident_sys_id).get("result", [])
        )

        return IncidentPackage(
            incident=incident,
            audit_events=audit_events,
            work_notes=work_notes,
            comments=comments,
        )

    def _normalize_audit(self, audit_rows: List[dict]) -> List[NormalizedEvent]:
        events: List[NormalizedEvent] = []

        for row in audit_rows:
            field_name = row.get("fieldname", "")
            event_type = "OTHER"

            if field_name == "state":
                event_type = "STATE_CHANGE"
            elif field_name in {"assignment_group", "assigned_to"}:
                event_type = "ASSIGNMENT_CHANGE"
            elif field_name in {"priority", "severity"}:
                event_type = "PRIORITY_CHANGE"
            elif field_name == "cmdb_ci":
                event_type = "CI_UPDATE"

            events.append(
                NormalizedEvent(
                    timestamp=row.get("sys_created_on", ""),
                    source="audit",
                    event_type=event_type,
                    author=row.get("user"),
                    author_type="unknown",
                    content=f"{field_name} changed from {row.get('oldvalue')} to {row.get('newvalue')}",
                    field_name=field_name,
                    old_value=row.get("oldvalue"),
                    new_value=row.get("newvalue"),
                )
            )

        return events

    def _normalize_journal(self, journal_rows: List[dict]) -> tuple[List[NormalizedEvent], List[NormalizedEvent]]:
        work_notes: List[NormalizedEvent] = []
        comments: List[NormalizedEvent] = []

        for row in journal_rows:
            element = row.get("element", "")
            event = NormalizedEvent(
                timestamp=row.get("sys_created_on", ""),
                source="work_note" if element == "work_notes" else "comment",
                event_type="WORK_NOTE" if element == "work_notes" else "COMMENT",
                author=row.get("sys_created_by"),
                author_type="unknown",
                content=row.get("value", "") or "",
            )

            if element == "work_notes":
                work_notes.append(event)
            else:
                comments.append(event)

        return work_notes, comments

    def _display_value(self, field: object) -> str | None:
        if isinstance(field, dict):
            return field.get("display_value") or field.get("value")
        if isinstance(field, str):
            return field
        return None
    
    def get_incident_by_number(self, number: str) -> Dict[str, Any]:
        return self._get(
            "/api/now/table/incident",
            {
                "sysparm_query": f"number={number}",
                "sysparm_limit": 1,
            },
    )    