# RCA Agent — Complete Backend

AI-powered Root Cause Analysis pipeline.
ServiceNow → Vertex AI / Gemini → Confluence. End-to-end automated.

## Services

| Service  | Stack                      | Port |
|----------|----------------------------|------|
| Backend  | Python, FastAPI, Vertex AI | 8080 |
| Frontend | Python, Streamlit          | 8501 |

## Project structure

```
rca-agent/
├── backend/
│   ├── main.py                   FastAPI app — init Gemini + ServiceNow + Confluence
│   ├── models.py                 All Pydantic schemas
│   ├── requirements.txt          fastapi, uvicorn, google-cloud-aiplatform, httpx
│   ├── Dockerfile
│   ├── routers/rca.py            All REST endpoints
│   ├── services/
│   │   ├── gemini.py             Vertex AI wrapper
│   │   ├── extraction.py         Stage 1 — data extraction
│   │   ├── timeline.py           Stage 2 — MTTR + timeline + Eureka
│   │   ├── quality.py            Stage 3 — quality scoring 0-100
│   │   ├── confluence.py         Stage 4 — generate post-mortem content
│   │   ├── servicenow.py         ServiceNow REST client (httpx async)
│   │   └── confluence_publish.py Confluence REST publisher (httpx async)
│   └── k8s/deployment.yaml       GKE: Deployment + Service + HPA
├── frontend/
│   ├── app.py                    Streamlit UI
│   ├── requirements.txt          streamlit, requests
│   ├── .streamlit/config.toml    Theme + server config
│   ├── Dockerfile
│   └── k8s/deployment.yaml       GKE: Deployment + Service + Ingress
├── k8s-shared.yaml               Namespace + ConfigMap + Workload Identity SA
├── k8s-secrets.yaml              K8s Secret template (ServiceNow + Confluence creds)
├── docker-compose.yml            Run both locally
├── backend.env.example           All backend env vars
├── test-backend.sh               curl test suite
└── README.md
```

## REST API endpoints

| Method | Endpoint                              | Description                                     |
|--------|---------------------------------------|-------------------------------------------------|
| POST   | /api/v1/rca/from-servicenow           | **Full end-to-end** — incident number in, Confluence page out |
| GET    | /api/v1/rca/servicenow/{number}       | Fetch raw incident from ServiceNow (no pipeline) |
| POST   | /api/v1/rca                           | Full pipeline — manual text input               |
| POST   | /api/v1/rca/extract                   | Stage 1 only                                    |
| POST   | /api/v1/rca/timeline                  | Stage 2 only                                    |
| POST   | /api/v1/rca/quality                   | Stage 3 only                                    |
| POST   | /api/v1/rca/confluence                | Stage 4 — generate content only (no publish)   |
| GET    | /health                               | Health + config status                          |
| GET    | /docs                                 | Swagger UI                                      |

## Setup

### 1. Create env files
```bash
cp backend.env.example backend.env
# Edit backend.env — fill in all values

cp frontend/.env.example frontend.env
# Set BACKEND_URL=http://localhost:8080
```

### 2. Authenticate with GCP (local dev)
```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
```

## Build and run

### Docker — build one image at a time
```bash
# Build
docker build -f backend/Dockerfile  -t rca-backend:latest  ./backend
docker build -f frontend/Dockerfile -t rca-frontend:latest ./frontend

# Run backend
docker run -d --name rca-backend -p 8080:8080 \
  --env-file backend.env \
  -v "$HOME/.config/gcloud:/tmp/gcloud:ro" \
  rca-backend:latest

# Run frontend
docker run -d --name rca-frontend -p 8501:8501 \
  --env-file frontend.env \
  rca-frontend:latest

# Check logs
docker logs -f rca-backend
docker logs -f rca-frontend
```

### Docker Compose — both together
```bash
docker compose up --build
```

### Local Python (no Docker)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat ../backend.env | grep -v ^# | xargs)
python -m backend.main
```

## Test the backend
```bash
chmod +x test-backend.sh
./test-backend.sh

# Or against Cloud Run / GKE
BACKEND=https://rca-backend-xxx.run.app ./test-backend.sh
```

## Key curl commands

```bash
# Health check
curl -s http://localhost:8080/health | jq .

# Test ServiceNow connection (no pipeline)
curl -s http://localhost:8080/api/v1/rca/servicenow/INC0091847 | jq .

# Full end-to-end (ServiceNow → Gemini → Confluence page created)
curl -s -X POST http://localhost:8080/api/v1/rca/from-servicenow \
  -H "Content-Type: application/json" \
  -d '{"incident_number":"INC0091847","publish_to_confluence":true}' | jq .

# Full end-to-end — dry run (no Confluence publish)
curl -s -X POST http://localhost:8080/api/v1/rca/from-servicenow \
  -H "Content-Type: application/json" \
  -d '{"incident_number":"INC0091847","publish_to_confluence":false}' | jq .
```

## Deploy to GKE

```bash
PROJECT_ID=your-project-id
REGION=us-central1

# 1. Create secrets (ServiceNow + Confluence creds)
kubectl create secret generic rca-agent-secrets \
  --namespace=rca-agent \
  --from-literal=SERVICENOW_INSTANCE=https://myco.service-now.com \
  --from-literal=SERVICENOW_USERNAME=svc_rca \
  --from-literal=SERVICENOW_PASSWORD=xxxx \
  --from-literal=CONFLUENCE_BASE_URL=https://myco.atlassian.net/wiki \
  --from-literal=CONFLUENCE_USERNAME=sre@myco.com \
  --from-literal=CONFLUENCE_API_TOKEN=xxxx \
  --from-literal=CONFLUENCE_SPACE_KEY=SRE \
  --from-literal=CONFLUENCE_PARENT_PAGE_ID=123456789

# 2. Apply shared resources
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s-shared.yaml
kubectl apply -f k8s-shared.yaml

# 3. Update image paths and apply deployments
sed -i "s/PROJECT_ID/$PROJECT_ID/g; s/REGION/$REGION/g" \
  backend/k8s/deployment.yaml frontend/k8s/deployment.yaml
kubectl apply -f backend/k8s/deployment.yaml
kubectl apply -f frontend/k8s/deployment.yaml

# 4. Verify
kubectl get pods -n rca-agent
kubectl get ingress rca-ingress -n rca-agent
kubectl logs -f deploy/rca-backend -n rca-agent
```

## Environment variables

### backend.env
| Variable | Required | Description |
|---|---|---|
| GCP_PROJECT_ID | Yes | GCP project ID |
| GCP_LOCATION | No | Vertex AI region (default: us-central1) |
| GEMINI_MODEL | No | gemini-1.5-pro or gemini-1.5-flash |
| SERVICENOW_INSTANCE | Yes* | https://your-instance.service-now.com |
| SERVICENOW_USERNAME | Yes* | ServiceNow username |
| SERVICENOW_PASSWORD | Yes* | ServiceNow password |
| CONFLUENCE_BASE_URL | Yes* | https://your-org.atlassian.net/wiki |
| CONFLUENCE_USERNAME | Yes* | Atlassian account email |
| CONFLUENCE_API_TOKEN | Yes* | API token from id.atlassian.net |
| CONFLUENCE_SPACE_KEY | Yes* | Space key e.g. SRE |
| CONFLUENCE_PARENT_PAGE_ID | No | Parent page ID for post-mortems |

*Required for /from-servicenow endpoint. Manual /api/v1/rca endpoint works without them.
