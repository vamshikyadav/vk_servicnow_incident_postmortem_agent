"""
ServiceNow REST API client.
Fetches incident details, audit log, and work notes for a given incident number.
Uses Basic Auth (username + password) or Bearer token — configured via env vars.
All calls are async using httpx.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

log = logging.getLogger("rca.servicenow")

# ── Config (loaded once at startup) ──────────────────────────────
SN_INSTANCE = ""        # e.g. https://mycompany.service-now.com
SN_USERNAME  = ""
SN_PASSWORD  = ""
SN_TIMEOUT   = 30       # seconds per request


def init_servicenow(instance: str, username: str, password: str) -> None:
    global SN_INSTANCE, SN_USERNAME, SN_PASSWORD
    SN_INSTANCE = instance.rstrip("/")
    SN_USERNAME  = username
    SN_PASSWORD  = password
    log.info("ServiceNow client initialised  instance=%s  user=%s", SN_INSTANCE, SN_USERNAME)


# ── Data classes ──────────────────────────────────────────────────
@dataclass
class SNIncident:
    sys_id:        str
    incident_id:   str          # e.g. INC0091847
    severity:      str
    ci:            str
    ci_sys_id:     str
    opened_at:     str
    closed_at:     str
    team:          str
    short_desc:    str
    description:   str
    resolution:    str
    state:         str
    assigned_to:   str
    work_notes_raw: str
    audit_entries:  list[dict]


# ── Internal helpers ──────────────────────────────────────────────
def _auth() -> httpx.BasicAuth:
    return httpx.BasicAuth(SN_USERNAME, SN_PASSWORD)


def _headers() -> dict:
    return {
        "Accept":       "application/json",
        "Content-Type": "application/json",
    }


def _sev_label(impact: str, urgency: str, priority: str) -> str:
    """Map ServiceNow priority/impact to a SEV label."""
    mapping = {"1": "SEV1 - Critical", "2": "SEV2 - Major", "3": "SEV3 - Minor"}
    return mapping.get(priority, f"Priority {priority}")


def _clean_html(text: str) -> str:
    """Strip basic HTML tags from work notes."""
    import re
    text = re.sub(r"<[^>]+>", "", text or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return text.strip()


# ── Public API ────────────────────────────────────────────────────

async def fetch_incident(incident_number: str) -> SNIncident:
    """
    Fetch a single incident by number (e.g. INC0091847).
    Pulls: incident record, CI name, work notes, audit log entries.
    """
    if not SN_INSTANCE:
        raise RuntimeError("ServiceNow not initialised — call init_servicenow() first")

    # Sanitize: uppercase and strip whitespace (ServiceNow is case-sensitive)
    incident_number = incident_number.strip().upper()

    async with httpx.AsyncClient(
        auth=_auth(),
        headers=_headers(),
        timeout=SN_TIMEOUT,
        follow_redirects=True,      # some SN instances redirect HTTP → HTTPS
    ) as client:

        # ── 1. Incident record ────────────────────────────────────
        log.info("Fetching incident %s from ServiceNow", incident_number)
        inc_resp = await client.get(
            f"{SN_INSTANCE}/api/now/table/incident",
            params={
                "sysparm_query":  f"number={incident_number}",
                "sysparm_limit":  "1",
                "sysparm_display_value": "all",   # return both value + display_value for reference fields
                "sysparm_fields": (
                    "sys_id,number,impact,urgency,priority,cmdb_ci,"
                    "opened_at,closed_at,assignment_group,short_description,"
                    "description,close_notes,work_notes,state,assigned_to"
                ),
            },
        )
        log.info("ServiceNow incident query status=%s url=%s", inc_resp.status_code, inc_resp.url)
        inc_resp.raise_for_status()
        inc_data = inc_resp.json()

        records = inc_data.get("result", [])
        if not records:
            log.error(
                "Incident %s not found. SN instance=%s response=%s",
                incident_number, SN_INSTANCE, inc_data
            )
            raise ValueError(
                f"Incident {incident_number} not found in ServiceNow. "
                f"Check the incident number, SN instance URL, and credentials."
            )

        inc = records[0]
        sys_id = inc.get("sys_id", "")
        log.info("Incident found  sys_id=%s", sys_id)

        # ── 2. CI name from CMDB ──────────────────────────────────
        ci_raw = inc.get("cmdb_ci", {})
        if isinstance(ci_raw, dict):
            ci_value   = ci_raw.get("value", "")
            ci_display = ci_raw.get("display_value", "")
        else:
            ci_value   = str(ci_raw)
            ci_display = ""
        ci_label = ci_display or "Unknown CI"

        if ci_value:
            try:
                ci_resp = await client.get(
                    f"{SN_INSTANCE}/api/now/table/cmdb_ci/{ci_value}",
                    params={"sysparm_fields": "name,sys_id"},
                )
                if ci_resp.is_success:
                    ci_data = ci_resp.json().get("result", {})
                    ci_label = ci_data.get("name", ci_label)
            except Exception as e:
                log.warning("Could not fetch CI details: %s", e)

        ci_string = f"{ci_label} (CMDB: {ci_value})" if ci_value else ci_label

        # ── 3. Work notes from journal entries ────────────────────
        log.info("Fetching work notes for sys_id=%s", sys_id)
        journal_resp = await client.get(
            f"{SN_INSTANCE}/api/now/table/sys_journal_field",
            params={
                "sysparm_query":  f"element_id={sys_id}^element=work_notes",
                "sysparm_fields": "sys_created_on,sys_created_by,value",
                "sysparm_orderby": "sys_created_on",
                "sysparm_limit":  "200",
            },
        )
        journal_resp.raise_for_status()
        journal_entries = journal_resp.json().get("result", [])

        work_notes_lines = []
        for entry in journal_entries:
            ts      = entry.get("sys_created_on", "")[:16]   # trim seconds
            author  = entry.get("sys_created_by", "system")
            content = _clean_html(entry.get("value", ""))
            if content:
                work_notes_lines.append(f"{ts} [{author}] {content}")

        # Also append the inline work_notes field if populated
        inline_notes = _clean_html(inc.get("work_notes", ""))
        if inline_notes and inline_notes not in "\n".join(work_notes_lines):
            work_notes_lines.append(inline_notes)

        work_notes_raw = "\n".join(work_notes_lines) if work_notes_lines else "(no work notes found)"

        # ── 4. Audit log ──────────────────────────────────────────
        log.info("Fetching audit log for sys_id=%s", sys_id)
        audit_resp = await client.get(
            f"{SN_INSTANCE}/api/now/table/sys_audit",
            params={
                "sysparm_query":  f"documentkey={sys_id}",
                "sysparm_fields": "sys_created_on,sys_created_by,fieldname,oldvalue,newvalue,reason",
                "sysparm_orderby": "sys_created_on",
                "sysparm_limit":  "500",
            },
        )
        audit_resp.raise_for_status()
        audit_entries = audit_resp.json().get("result", [])
        log.info("Audit entries retrieved: %d", len(audit_entries))

        # ── 5. Resolution notes ───────────────────────────────────
        resolution = _clean_html(inc.get("close_notes", "")) or _clean_html(inc.get("description", ""))

        # ── 6. Team / assignment group ────────────────────────────
        ag_raw = inc.get("assignment_group", {})
        team   = ag_raw.get("display_value", "") if isinstance(ag_raw, dict) else str(ag_raw)

        at_raw       = inc.get("assigned_to", {})
        assigned_to  = at_raw.get("display_value", "") if isinstance(at_raw, dict) else str(at_raw)

        return SNIncident(
            sys_id        = sys_id,
            incident_id   = inc.get("number", incident_number),
            severity      = _sev_label(
                inc.get("impact","3"), inc.get("urgency","3"), inc.get("priority","3")
            ),
            ci            = ci_string,
            ci_sys_id     = ci_value,
            opened_at     = inc.get("opened_at", ""),
            closed_at     = inc.get("closed_at", ""),
            team          = team or assigned_to or "Unknown",
            short_desc    = inc.get("short_description", ""),
            description   = _clean_html(inc.get("description", "")),
            resolution    = resolution,
            state         = inc.get("state", ""),
            assigned_to   = assigned_to,
            work_notes_raw = work_notes_raw,
            audit_entries  = audit_entries,
        )


async def format_audit_for_llm(incident: SNIncident) -> str:
    """
    Combine work notes + key audit trail into a single text block
    suitable for passing to the Gemini prompt.
    Filters out noise (password resets, UI tweaks, etc.).
    """
    SKIP_FIELDS = {
        "sys_updated_on", "sys_mod_count", "upon_approval", "upon_reject",
        "approval_history", "sla_due", "calendar_stc", "escalation",
        "business_stc", "time_worked",
    }

    lines = [incident.work_notes_raw, ""]

    if incident.audit_entries:
        lines.append("--- Audit trail ---")
        for entry in incident.audit_entries:
            field = entry.get("fieldname", "")
            if field in SKIP_FIELDS:
                continue
            ts      = entry.get("sys_created_on", "")[:16]
            by      = entry.get("sys_created_by", "system")
            old_val = entry.get("oldvalue", "")
            new_val = entry.get("newvalue", "")
            reason  = entry.get("reason", "")
            line    = f"{ts} [audit] {by} changed {field}: '{old_val}' → '{new_val}'"
            if reason:
                line += f"  ({reason})"
            lines.append(line)

    return "\n".join(lines)
