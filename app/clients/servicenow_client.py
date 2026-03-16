import requests
from typing import Any, Dict, List
from app.config import settings


class ServiceNowClient:
    def __init__(self) -> None:
        self.base_url = settings.servicenow_base_url.rstrip("/")
        self.auth = (settings.servicenow_username, settings.servicenow_password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_incident(self, sys_id: str) -> Dict[str, Any]:
        return self._get(
            "/api/now/table/incident",
            {
                "sysparm_query": f"sys_id={sys_id}",
                "sysparm_limit": 1,
            },
        )

    def get_audit_events(self, incident_sys_id: str) -> Dict[str, Any]:
        return self._get(
            "/api/now/table/sys_audit",
            {
                "sysparm_query": f"documentkey={incident_sys_id}",
                "sysparm_limit": 1000,
                "sysparm_orderby": "sys_created_on",
            },
        )

    def get_journal_entries(self, incident_sys_id: str) -> Dict[str, Any]:
        return self._get(
            "/api/now/table/sys_journal_field",
            {
                "sysparm_query": f"element_id={incident_sys_id}",
                "sysparm_limit": 1000,
                "sysparm_orderby": "sys_created_on",
            },
        )