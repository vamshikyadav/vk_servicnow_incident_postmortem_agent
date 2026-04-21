#!/bin/bash
# =============================================================================
# RCA Agent — Backend curl test script
# Usage:
#   chmod +x test-backend.sh
#   ./test-backend.sh                         # tests localhost:8080
#   BACKEND=https://rca-backend-xxx.run.app ./test-backend.sh
# =============================================================================

BACKEND="${BACKEND:-http://localhost:8080}"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() { echo -e "${GREEN}  PASS${NC}  $1"; }
fail() { echo -e "${RED}  FAIL${NC}  $1"; }
info() { echo -e "${BLUE}  ----${NC}  $1"; }
head() { echo -e "\n${YELLOW}══ $1 ══${NC}"; }

echo ""
echo "================================================================="
echo " RCA Agent — Backend test suite"
echo " Target: $BACKEND"
echo "================================================================="

# ---------------------------------------------------------------------------
# PAYLOAD — reused by all pipeline tests
# ---------------------------------------------------------------------------
PAYLOAD='{
  "incident_id":      "INC0091847",
  "severity":         "SEV2 - Major",
  "ci":               "payments-api (CMDB: CI-00291)",
  "opened_at":        "2025-06-14 02:17 UTC",
  "closed_at":        "2025-06-14 05:44 UTC",
  "team":             "Platform Reliability Engineering",
  "work_notes":       "02:17 - Alert fired: payment gateway timeout rate > 15%\n02:21 - On-call engineer paged (Arjun S.)\n02:34 - Arjun acknowledged. High error rate on payments-api pods.\n02:55 - Suspected DB connection pool exhaustion. Increased pool size. No improvement.\n03:12 - AUTOMATED: health check retry policy triggered\n03:28 - Ravi joined. Config change at 01:55 UTC reduced max_connections from 200 to 20.\n03:31 - Config rollback initiated.\n03:44 - Error rates returning to normal.\n04:02 - AUTOMATED: alert resolved\n05:44 - Incident closed.",
  "resolution_notes": "Root cause: misconfigured max_connections in payments-api config deployed at 01:55 UTC. Reduced pool limit from 200 to 20 causing exhaustion. Rolled back at 03:31 UTC. Prevention: add CI/CD config validation step."
}'

SN_PAYLOAD='{
  "incident_number":       "INC0091847",
  "publish_to_confluence": false
}'

run_test() {
  local name="$1"
  local method="$2"
  local url="$3"
  local data="$4"
  local check_field="$5"

  if [ "$method" = "GET" ]; then
    resp=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
  else
    resp=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -d "$data" 2>/dev/null)
  fi

  http_code=$(echo "$resp" | tail -1)
  body=$(echo "$resp" | head -n -1)

  if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
    if [ -n "$check_field" ]; then
      field_val=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$check_field','MISSING'))" 2>/dev/null)
      if [ "$field_val" = "MISSING" ] || [ -z "$field_val" ]; then
        fail "$name — HTTP $http_code but field '$check_field' missing in response"
      else
        pass "$name — HTTP $http_code  |  $check_field=$field_val"
      fi
    else
      pass "$name — HTTP $http_code"
    fi
  else
    fail "$name — HTTP $http_code"
    echo "     Response: $(echo "$body" | head -c 200)"
  fi
}

# ===========================================================================
# 1. HEALTH CHECK
# ===========================================================================
head "1. Health check"

run_test "GET /health" GET "$BACKEND/health" "" "status"

# Show full health details
echo ""
info "Full health response:"
curl -s "$BACKEND/health" | python3 -m json.tool 2>/dev/null || \
  curl -s "$BACKEND/health"

# ===========================================================================
# 2. SERVICENOW CONNECTIVITY
# ===========================================================================
head "2. ServiceNow — fetch incident (no pipeline)"
info "Tests your ServiceNow connection. Requires SERVICENOW_* env vars set."

run_test \
  "GET /api/v1/rca/servicenow/INC0091847" \
  GET \
  "$BACKEND/api/v1/rca/servicenow/INC0091847" \
  "" \
  "incident_id"

echo ""
info "Full ServiceNow fetch response:"
curl -s "$BACKEND/api/v1/rca/servicenow/INC0091847" | python3 -m json.tool 2>/dev/null

# ===========================================================================
# 3. INDIVIDUAL PIPELINE STAGES (manual text input)
# ===========================================================================
head "3. Stage 1 — Data extraction"
run_test \
  "POST /api/v1/rca/extract" \
  POST \
  "$BACKEND/api/v1/rca/extract" \
  "$PAYLOAD" \
  "incident_id"

echo ""
info "Extraction result (human notes only):"
curl -s -X POST "$BACKEND/api/v1/rca/extract" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Incident:   {d.get('incident_id')}\")
print(f\"  CI attached: {d.get('ci_attached')}\")
print(f\"  Noise filtered: {d.get('automated_entries_filtered')}\")
print(f\"  Human notes: {len(d.get('human_notes', []))}\")
print(f\"  Key actors: {d.get('key_actors')}\")
" 2>/dev/null

head "4. Stage 2 — Timeline & analysis"
run_test \
  "POST /api/v1/rca/timeline" \
  POST \
  "$BACKEND/api/v1/rca/timeline" \
  "$PAYLOAD" \
  "mttr_minutes"

echo ""
info "Timeline metrics:"
curl -s -X POST "$BACKEND/api/v1/rca/timeline" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  MTTR:            {d.get('mttr_minutes')} min\")
print(f\"  Time to detect:  {d.get('time_to_detect_minutes')} min\")
print(f\"  Time to diagnose:{d.get('time_to_diagnose_minutes')} min\")
print(f\"  Time to fix:     {d.get('time_to_fix_minutes')} min\")
em = d.get('eureka_moment', {})
print(f\"  Eureka moment:   {em.get('time')} — {em.get('description','')[:80]}\")
print(f\"  Timeline events: {len(d.get('timeline', []))}\")
" 2>/dev/null

head "5. Stage 3 — Quality validation"
run_test \
  "POST /api/v1/rca/quality" \
  POST \
  "$BACKEND/api/v1/rca/quality" \
  "$PAYLOAD" \
  "quality_score"

echo ""
info "Quality result:"
curl -s -X POST "$BACKEND/api/v1/rca/quality" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Score:   {d.get('quality_score')}/100\")
print(f\"  Quality: {d.get('overall_quality')}\")
for c in d.get('checks', []):
    icon = '✓' if c['passed'] else ('△' if c['severity']=='warn' else '✗')
    print(f\"  {icon}  {c['name']}: {c['detail'][:60]}\")
" 2>/dev/null

head "6. Stage 4 — Confluence content generation"
run_test \
  "POST /api/v1/rca/confluence" \
  POST \
  "$BACKEND/api/v1/rca/confluence" \
  "$PAYLOAD" \
  "page_title"

echo ""
info "Confluence content:"
curl -s -X POST "$BACKEND/api/v1/rca/confluence" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Page title: {d.get('page_title')}\")
print(f\"  Sections:   {len(d.get('sections', []))}\")
print(f\"  Action items: {len(d.get('action_items', []))}\")
print(f\"  Tags: {d.get('tags')}\")
" 2>/dev/null

# ===========================================================================
# 4. FULL PIPELINE — manual text input
# ===========================================================================
head "7. Full pipeline — manual text input (all 4 stages)"
run_test \
  "POST /api/v1/rca" \
  POST \
  "$BACKEND/api/v1/rca" \
  "$PAYLOAD" \
  "status"

echo ""
info "Full pipeline summary:"
curl -s -X POST "$BACKEND/api/v1/rca" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Status:     {d.get('status')}\")
print(f\"  Extraction: {'OK' if d.get('extraction') else 'FAILED'}\")
print(f\"  Timeline:   {'OK' if d.get('timeline') else 'FAILED'}\")
print(f\"  Quality:    {'OK — ' + str(d.get('quality',{}).get('quality_score')) + '/100' if d.get('quality') else 'FAILED'}\")
print(f\"  Confluence: {'OK — ' + d.get('confluence',{}).get('page_title','') if d.get('confluence') else 'FAILED'}\")
errs = d.get('errors', {})
if errs:
    print(f\"  Errors: {list(errs.keys())}\")
" 2>/dev/null

# ===========================================================================
# 5. END-TO-END — ServiceNow → Gemini → Confluence
# ===========================================================================
head "8. End-to-end — ServiceNow fetch + full pipeline (no publish)"
info "Requires SERVICENOW_* env vars. publish_to_confluence=false so no Confluence page created."

run_test \
  "POST /api/v1/rca/from-servicenow" \
  POST \
  "$BACKEND/api/v1/rca/from-servicenow" \
  "$SN_PAYLOAD" \
  "status"

echo ""
info "End-to-end summary:"
curl -s -X POST "$BACKEND/api/v1/rca/from-servicenow" \
  -H "Content-Type: application/json" \
  -d "$SN_PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"  Status:          {d.get('status')}\")
sn = d.get('servicenow_fetch', {})
if sn:
    print(f\"  SN incident:     {sn.get('incident_id')}\")
    print(f\"  SN audit entries:{sn.get('audit_count')}\")
    print(f\"  SN work notes:   {len(sn.get('work_notes_raw',''))} chars\")
print(f\"  Extraction:      {'OK' if d.get('extraction') else 'FAILED'}\")
print(f\"  Timeline MTTR:   {d.get('timeline',{}).get('mttr_minutes','—')} min\")
print(f\"  Quality score:   {d.get('quality',{}).get('quality_score','—')}/100\")
print(f\"  Confluence page: {d.get('confluence',{}).get('page_title','—')}\")
pub = d.get('confluence_page_published')
if pub:
    print(f\"  Published URL:   {pub.get('page_url')}\")
errs = d.get('errors', {})
if errs:
    print(f\"  Errors:          {list(errs.keys())}\")
" 2>/dev/null

# ===========================================================================
# 6. END-TO-END WITH PUBLISH
# ===========================================================================
head "9. End-to-end — ServiceNow + pipeline + Confluence PUBLISH"
info "This will CREATE a real page in Confluence. Only run when ready."
echo -e "  ${YELLOW}Skipped by default. Uncomment the block in the script to enable.${NC}"

# Uncomment to enable:
# run_test \
#   "POST /api/v1/rca/from-servicenow (publish=true)" \
#   POST \
#   "$BACKEND/api/v1/rca/from-servicenow" \
#   '{"incident_number":"INC0091847","publish_to_confluence":true}' \
#   "status"

# ===========================================================================
# SUMMARY
# ===========================================================================
echo ""
echo "================================================================="
echo " Done. Open Swagger UI for interactive testing:"
echo " $BACKEND/docs"
echo "================================================================="
echo ""
