"""
RCA Agent — Streamlit frontend
Talks to the FastAPI backend via REST API.
Configure BACKEND_URL in frontend.env or environment variable.
"""
import os
import json
import requests
import streamlit as st
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8080").rstrip("/")

# ── Page setup ────────────────────────────────────────────────────
st.set_page_config(
    page_title="RCA Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F8F7F2; }
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #E8E7E2;
        border-radius: 10px;
        padding: 14px 18px;
    }

    /* Stage expanders */
    details summary {
        font-weight: 500;
        font-size: 15px;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] > div {
        background-color: white;
        border-right: 1px solid #E8E7E2;
    }

    /* Status badges */
    .badge-pending  { background:#E8E7E2; color:#5F5E5A; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
    .badge-running  { background:#E6F1FB; color:#0C447C; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
    .badge-done     { background:#E1F5EE; color:#085041; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
    .badge-error    { background:#FCEBEB; color:#A32D2D; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }
    .badge-warn     { background:#FAEEDA; color:#633806; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:600; }

    /* Eureka box */
    .eureka-box {
        background: #FAEEDA;
        border: 1px solid #EF9F27;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
    }

    /* Timeline item */
    .tl-item {
        border-left: 3px solid #E8E7E2;
        padding: 6px 0 6px 16px;
        margin: 4px 0;
    }

    /* Quality check rows */
    .check-pass { background:#EAF3DE; border-radius:6px; padding:8px 14px; margin:4px 0; }
    .check-warn { background:#FAEEDA; border-radius:6px; padding:8px 14px; margin:4px 0; }
    .check-fail { background:#FCEBEB; border-radius:6px; padding:8px 14px; margin:4px 0; }

    /* Confluence preview */
    .confluence-preview {
        background: #FAFAF8;
        border: 1px solid #E8E7E2;
        border-radius: 10px;
        padding: 20px 24px;
        font-family: Georgia, serif;
    }

    /* Code block */
    .stCode { border-radius: 8px; }

    h1 { color: #1A5276 !important; }
    h2 { color: #0E6655 !important; }
    h3 { color: #2C3E50 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sample data ───────────────────────────────────────────────────
SAMPLE = {
    "incident_id": "INC0091847",
    "severity": "SEV2 - Major",
    "ci": "payments-api (CMDB: CI-00291)",
    "opened_at": "2025-06-14 02:17 UTC",
    "closed_at": "2025-06-14 05:44 UTC",
    "team": "Platform Reliability Engineering",
    "work_notes": """02:17 - Alert fired: payment gateway timeout rate > 15%
02:21 - On-call engineer paged (Arjun S.)
02:34 - Arjun acknowledged. Checked dashboards — high error rate on payments-api pods.
02:55 - Suspected DB connection pool exhaustion. Increased pool size. No improvement.
03:12 - AUTOMATED: health check retry policy triggered
03:28 - Ravi joined. Reviewed recent deploys. Noted config change at 01:55 UTC reduced max_connections for payments-api from 200 to 20.
03:31 - Config rollback initiated on payments-api.
03:44 - Error rates returning to normal. Payment success rate recovering.
04:02 - AUTOMATED: alert resolved by monitoring system
05:44 - Incident formally closed. Post-mortem scheduled.""",
    "resolution_notes": """Root cause identified as a misconfigured max_connections value in payments-api config deployed at 01:55 UTC. A routine config update incorrectly set the DB connection pool limit to 20 (down from 200), causing exhaustion under normal load. Rolled back config at 03:31 UTC. Recovery confirmed at 03:44 UTC. Future prevention: add config validation step in CI/CD pipeline to flag anomalous connection pool values.""",
}

# ── Session state init ────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = None
if "stage_status" not in st.session_state:
    st.session_state.stage_status = {
        "extraction": "pending",
        "timeline":   "pending",
        "quality":    "pending",
        "confluence": "pending",
    }
if "last_error" not in st.session_state:
    st.session_state.last_error = None

# ── API helpers ───────────────────────────────────────────────────
def call_api(endpoint: str, payload: dict) -> dict:
    url = f"{BACKEND_URL}{endpoint}"
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()

def health_check() -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return r.json() if r.ok else None
    except Exception:
        return None

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 RCA Agent")
    st.markdown("*Incident Analysis Pipeline*")
    st.divider()

    # Backend health
    st.markdown("**Backend status**")
    health = health_check()
    if health:
        st.success(f"✓ Connected  \n`{health.get('model','—')}`")
        st.caption(f"Project: `{health.get('project','—')}`  \nRegion: `{health.get('location','—')}`")
    else:
        st.error(f"✗ Cannot reach backend  \n`{BACKEND_URL}`")

    st.divider()
    st.markdown("**Pipeline stages**")

    status_icons = {
        "pending": "⬜",
        "running": "🔄",
        "done":    "✅",
        "warn":    "⚠️",
        "error":   "❌",
    }
    stage_labels = {
        "extraction": "1 · Data extraction",
        "timeline":   "2 · Timeline & analysis",
        "quality":    "3 · Quality validation",
        "confluence": "4 · Confluence delivery",
    }
    for key, label in stage_labels.items():
        icon = status_icons[st.session_state.stage_status[key]]
        st.markdown(f"{icon} {label}")

    st.divider()
    st.markdown("**REST API docs**")
    st.markdown(f"[Swagger UI]({BACKEND_URL}/docs)  |  [ReDoc]({BACKEND_URL}/redoc)")
    st.caption(f"Backend: `{BACKEND_URL}`")

# ── Main ──────────────────────────────────────────────────────────
st.title("Incident RCA Generator")
st.markdown("Fill in the incident details below and run the full AI-powered analysis pipeline. The backend is also usable as a standalone REST API.")

# ── Incident form ─────────────────────────────────────────────────
with st.form("incident_form"):
    st.subheader("Incident details")

    col1, col2 = st.columns(2)
    with col1:
        incident_id = st.text_input("Incident ID", value=SAMPLE["incident_id"])
        ci          = st.text_input("Affected service / CI", value=SAMPLE["ci"])
        opened_at   = st.text_input("Incident opened", value=SAMPLE["opened_at"])

    with col2:
        severity  = st.selectbox("Severity", ["SEV1 - Critical","SEV2 - Major","SEV3 - Minor"], index=1)
        team      = st.text_input("Assigned team", value=SAMPLE["team"])
        closed_at = st.text_input("Incident resolved", value=SAMPLE["closed_at"])

    work_notes       = st.text_area("Work notes (raw ServiceNow export)", value=SAMPLE["work_notes"], height=180)
    resolution_notes = st.text_area("Resolution notes (from assignee)", value=SAMPLE["resolution_notes"], height=100)

    col_run, col_reset, _ = st.columns([2, 1, 5])
    with col_run:
        submitted = st.form_submit_button("▶  Run full RCA pipeline", type="primary", use_container_width=True)
    with col_reset:
        reset = st.form_submit_button("Reset", use_container_width=True)

# ── Reset ─────────────────────────────────────────────────────────
if reset:
    st.session_state.results = None
    st.session_state.last_error = None
    st.session_state.stage_status = {k: "pending" for k in st.session_state.stage_status}
    st.rerun()

# ── Run pipeline ──────────────────────────────────────────────────
if submitted:
    st.session_state.last_error = None
    payload = {
        "incident_id":      incident_id,
        "severity":         severity,
        "ci":               ci,
        "opened_at":        opened_at,
        "closed_at":        closed_at,
        "team":             team,
        "work_notes":       work_notes,
        "resolution_notes": resolution_notes,
    }

    # Reset statuses
    st.session_state.stage_status = {k: "running" for k in st.session_state.stage_status}
    st.session_state.results = None

    progress_bar = st.progress(0, text="Running pipeline…")

    try:
        progress_bar.progress(10, text="Stage 1 — Extracting incident data…")
        results = call_api("/api/v1/rca", payload)
        progress_bar.progress(100, text="Pipeline complete!")

        st.session_state.results = results
        st.session_state.stage_status = {
            "extraction": "done"  if results.get("extraction") else "error",
            "timeline":   "done"  if results.get("timeline")   else ("error" if results.get("errors", {}).get("timeline") else "done"),
            "quality":    ("warn" if results.get("quality", {}).get("overall_quality") == "low" else "done") if results.get("quality") else "error",
            "confluence": "done"  if results.get("confluence") else ("error" if results.get("errors", {}).get("confluence") else "done"),
        }

    except requests.exceptions.ConnectionError:
        st.session_state.last_error = f"Cannot connect to backend at {BACKEND_URL}. Is it running?"
        st.session_state.stage_status = {k: "error" for k in st.session_state.stage_status}
    except requests.exceptions.HTTPError as e:
        st.session_state.last_error = f"Backend error: {e.response.status_code} — {e.response.text[:200]}"
        st.session_state.stage_status = {k: "error" for k in st.session_state.stage_status}
    except Exception as e:
        st.session_state.last_error = str(e)
        st.session_state.stage_status = {k: "error" for k in st.session_state.stage_status}

    progress_bar.empty()
    st.rerun()

# ── Error banner ──────────────────────────────────────────────────
if st.session_state.last_error:
    st.error(f"**Pipeline error:** {st.session_state.last_error}")

# ── Results ───────────────────────────────────────────────────────
if st.session_state.results:
    r = st.session_state.results
    st.divider()

    # ── Stage 1: Extraction ───────────────────────────────────────
    with st.expander("**Stage 1 — Data extraction**  ✅", expanded=True):
        ext = r.get("extraction")
        if ext:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Incident ID:** `{ext.get('incident_id','—')}`")
                st.markdown(f"**Severity:** `{ext.get('severity','—')}`")
                st.markdown(f"**CI:** {ext.get('ci_name','—')} {'🟢 CI attached' if ext.get('ci_attached') else '🟡 No CI'}")
                st.markdown(f"**Team:** {ext.get('team','—')}")
            with col2:
                st.markdown(f"**Key actors:** {', '.join(ext.get('key_actors', [])) or '—'}")
                st.markdown(f"**Affected components:** {', '.join(ext.get('affected_components', [])) or '—'}")
                st.markdown(f"**Automated entries filtered:** `{ext.get('automated_entries_filtered', 0)}`")

            st.markdown("**Human work notes**")
            notes = ext.get("human_notes", [])
            if notes:
                rows = [{"Time": n["time"], "Note": n["note"]} for n in notes]
                st.table(rows)
            else:
                st.info("No human notes extracted.")
        else:
            st.error("Extraction stage failed.")
            if r.get("errors", {}).get("extraction"):
                st.code(r["errors"]["extraction"])

    # ── Stage 2: Timeline ─────────────────────────────────────────
    with st.expander("**Stage 2 — Timeline & analysis**  ✅", expanded=True):
        tl = r.get("timeline")
        if tl:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("MTTR",            f"{tl.get('mttr_minutes','—')} min")
            m2.metric("Time to detect",  f"{tl.get('time_to_detect_minutes','—')} min")
            m3.metric("Time to diagnose",f"{tl.get('time_to_diagnose_minutes','—')} min")
            m4.metric("Time to fix",     f"{tl.get('time_to_fix_minutes','—')} min")

            eureka = tl.get("eureka_moment", {})
            if eureka:
                st.markdown(f"""
<div class="eureka-box">
<strong>⚡ Eureka moment — {eureka.get('time','')}</strong><br>
{eureka.get('description','')}
</div>""", unsafe_allow_html=True)

            if tl.get("narrative_summary"):
                st.info(tl["narrative_summary"])

            st.markdown("**Event timeline**")
            cat_icons = {
                "detection":     "🔴",
                "investigation": "🟡",
                "diagnosis":     "🔵",
                "fix":           "🟢",
                "recovery":      "✅",
            }
            for ev in tl.get("timeline", []):
                icon = "⚡" if ev.get("is_eureka") else cat_icons.get(ev.get("category",""), "⚪")
                st.markdown(
                    f"<div class='tl-item'>{icon} <strong>{ev.get('time','')}</strong> — "
                    f"{ev.get('event','')} <code>{ev.get('category','')}</code></div>",
                    unsafe_allow_html=True
                )
        else:
            st.error("Timeline stage failed.")
            if r.get("errors", {}).get("timeline"):
                st.code(r["errors"]["timeline"])

    # ── Stage 3: Quality ──────────────────────────────────────────
    qual_icon = {"high":"✅","medium":"⚠️","low":"❌"}.get(
        r.get("quality",{}).get("overall_quality","medium"), "⚠️")
    with st.expander(f"**Stage 3 — Quality validation**  {qual_icon}", expanded=True):
        q = r.get("quality")
        if q:
            score = q.get("quality_score", 0)
            quality_level = q.get("overall_quality", "medium")
            color = {"high":"green","medium":"orange","low":"red"}.get(quality_level,"orange")

            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Quality score", f"{score}/100")
            with col2:
                st.markdown(f"**Overall:** :{color}[{quality_level.upper()} QUALITY RCA]")

            st.markdown("**Quality checks**")
            for check in q.get("checks", []):
                css_class = "check-pass" if check["passed"] else ("check-warn" if check["severity"]=="warn" else "check-fail")
                icon = "✓" if check["passed"] else ("△" if check["severity"]=="warn" else "✗")
                st.markdown(
                    f"<div class='{css_class}'><strong>{icon} {check['name']}</strong><br>"
                    f"<small>{check['detail']}</small></div>",
                    unsafe_allow_html=True
                )

            if q.get("recommendations"):
                st.markdown("**Recommendations**")
                for rec in q["recommendations"]:
                    st.markdown(f"→ {rec}")
        else:
            st.error("Quality stage failed.")

    # ── Stage 4: Confluence ───────────────────────────────────────
    with st.expander("**Stage 4 — Confluence delivery**  ✅", expanded=True):
        conf = r.get("confluence")
        if conf:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Page title:** {conf.get('page_title','')}")
                if conf.get("tags"):
                    st.markdown(" ".join([f"`{t}`" for t in conf["tags"]]))
            with col2:
                if st.button("📋  Copy page content", use_container_width=True):
                    # Build plain text version for clipboard
                    lines = [conf.get("page_title",""), "="*60]
                    for s in conf.get("sections", []):
                        lines += ["", s["heading"], "-"*40, s["content"]]
                    if conf.get("action_items"):
                        lines += ["", "Action Items", "-"*40]
                        for a in conf["action_items"]:
                            lines.append(f"[ ] {a['task']}  |  Owner: {a['owner']}  |  Due: {a['due']}")
                    st.session_state["conf_text"] = "\n".join(lines)
                    st.success("Copied to session — see text area below")

            # Confluence page preview
            st.markdown("**Post-mortem preview**")
            preview_html = f"<div class='confluence-preview'>"
            preview_html += f"<h2>{conf.get('page_title','')}</h2>"
            for section in conf.get("sections", []):
                preview_html += f"<h3>{section['heading']}</h3><p>{section['content']}</p>"

            if conf.get("action_items"):
                preview_html += "<h3>Action items</h3><table style='width:100%;border-collapse:collapse;font-family:sans-serif;font-size:13px'>"
                preview_html += "<tr style='background:#DFE1E6'><th style='padding:6px 10px;text-align:left'>Owner</th><th style='padding:6px 10px;text-align:left'>Task</th><th style='padding:6px 10px;text-align:left'>Due</th></tr>"
                for a in conf["action_items"]:
                    preview_html += f"<tr style='border-bottom:1px solid #eee'><td style='padding:6px 10px'>{a['owner']}</td><td style='padding:6px 10px'>{a['task']}</td><td style='padding:6px 10px'>{a['due']}</td></tr>"
                preview_html += "</table>"
            preview_html += "</div>"
            st.markdown(preview_html, unsafe_allow_html=True)

            # Copyable text area
            if "conf_text" in st.session_state:
                st.text_area("Page content (plain text)", value=st.session_state["conf_text"], height=200)
        else:
            st.error("Confluence stage failed.")
            if r.get("errors", {}).get("confluence"):
                st.code(r["errors"]["confluence"])

    # ── Raw JSON (debug) ──────────────────────────────────────────
    with st.expander("Raw API response (debug)"):
        st.json(r)
