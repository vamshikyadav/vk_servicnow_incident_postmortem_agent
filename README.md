# RCA Agent

AI-powered Root Cause Analysis pipeline. Two independently deployable services:

- **Backend** — Python / FastAPI / Vertex AI (Gemini). Full REST API.
- **Frontend** — React / Vite / Nginx. Standalone UI.

## Project structure

```
rca-agent/
├── backend/
│   ├── main.py               FastAPI app, CORS, health
│   ├── models.py             Pydantic schemas
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/rca.py        All REST endpoints
│   ├── services/
│   │   ├── gemini.py         Vertex AI wrapper
│   │   ├── extraction.py     Stage 1
│   │   ├── timeline.py       Stage 2
│   │   ├── quality.py        Stage 3
│   │   └── confluence.py     Stage 4
│   └── k8s/deployment.yaml
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js            REST client
│   │   ├── stages.jsx        Stage result panels
│   │   └── components.jsx
│   ├── nginx.conf
│   ├── docker-entrypoint.sh
│   ├── Dockerfile
│   └── k8s/deployment.yaml
├── k8s-shared.yaml           Namespace + ConfigMap + WorkloadIdentity SA
├── docker-compose.yml
├── cloudbuild.yaml
└── README.md
```

## REST API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/rca` | Full pipeline |
| POST | `/api/v1/rca/extract` | Stage 1 only |
| POST | `/api/v1/rca/timeline` | Stage 2 only |
| POST | `/api/v1/rca/quality` | Stage 3 only |
| POST | `/api/v1/rca/confluence` | Stage 4 only |
| GET | `/docs` | Swagger UI |
| GET | `/health` | Health check |

## Prerequisites

```bash
gcloud services enable aiplatform.googleapis.com --project=YOUR_PROJECT_ID
gcloud auth application-default login
```

## Local dev (Docker Compose — both services)

```bash
cp .env.example .env          # set GCP_PROJECT_ID
docker compose up --build

# Frontend : http://localhost:3000
# Backend  : http://localhost:8080
# Swagger  : http://localhost:8080/docs
```

## Run services separately (no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GCP_PROJECT_ID=your-project-id
python -m backend.main

# Frontend (new terminal)
cd frontend
npm install
npm run dev          # proxies /api to localhost:8080 automatically
```

## Docker — run separately

```bash
# Backend
docker build -t rca-backend ./backend
docker run -d --name rca-backend -p 8080:8080 \
  -e GCP_PROJECT_ID=your-project-id \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcloud/application_default_credentials.json \
  -v "$HOME/.config/gcloud:/tmp/gcloud:ro" \
  rca-backend

# Frontend — inject backend URL at runtime, no rebuild needed
docker build -t rca-frontend ./frontend
docker run -d --name rca-frontend -p 3000:80 \
  -e VITE_API_URL=http://localhost:8080 \
  rca-frontend
```

## Deploy to Cloud Run

```bash
PROJECT_ID=your-project-id
REGION=us-central1

# Create Artifact Registry repo (one-time)
gcloud artifacts repositories create rca-agent \
  --repository-format=docker --location=$REGION --project=$PROJECT_ID

# Build + deploy both services via Cloud Build
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=$REGION --project=$PROJECT_ID

# Or deploy backend manually, then frontend with backend URL
gcloud run deploy rca-backend \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-backend:latest \
  --region=$REGION --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GEMINI_MODEL=gemini-1.5-pro"

BACKEND_URL=$(gcloud run services describe rca-backend \
  --region=$REGION --format='value(status.url)')

gcloud run deploy rca-frontend \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-frontend:latest \
  --region=$REGION --allow-unauthenticated \
  --set-env-vars="VITE_API_URL=$BACKEND_URL"
```

## Deploy to GKE

```bash
PROJECT_ID=your-project-id
REGION=us-central1

# One-time: create GCP SA and bind Workload Identity
gcloud iam service-accounts create rca-agent-sa --project=$PROJECT_ID
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rca-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
gcloud iam service-accounts add-iam-policy-binding \
  rca-agent-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:$PROJECT_ID.svc.id.goog[rca-agent/rca-agent-sa]"

# Fill in project / region in manifests
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" k8s-shared.yaml
sed -i "s/PROJECT_ID/$PROJECT_ID/g; s/REGION/$REGION/g" \
  backend/k8s/deployment.yaml frontend/k8s/deployment.yaml

# Apply
kubectl apply -f k8s-shared.yaml
kubectl apply -f backend/k8s/deployment.yaml
kubectl apply -f frontend/k8s/deployment.yaml

# Get ingress IP
kubectl get ingress rca-ingress -n rca-agent
```

## Environment variables

### Backend
| Variable | Default | Description |
|---|---|---|
| `GCP_PROJECT_ID` | required | GCP project ID |
| `GCP_LOCATION` | `us-central1` | Vertex AI region |
| `GEMINI_MODEL` | `gemini-1.5-pro` | Gemini model |
| `CORS_ORIGINS` | localhost | Comma-separated allowed origins |

### Frontend
| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | (empty) | Backend URL. Empty = same origin |

## Runtime URL injection (no rebuild per env)

The frontend image bakes `__VITE_API_URL_PLACEHOLDER__` into the JS bundle at build time. `docker-entrypoint.sh` replaces it with `$VITE_API_URL` when the container starts — so **one image works in dev, staging, and prod** with just an env var change.
