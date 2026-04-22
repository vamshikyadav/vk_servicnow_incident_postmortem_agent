# RCA Agent — Helm Charts

Two Helm charts for deploying the RCA Agent on GKE:

| Chart | Description | Port |
|---|---|---|
| `rca-backend` | FastAPI + Vertex AI + ServiceNow + Confluence | 8080 |
| `rca-frontend` | Streamlit UI | 8501 |

## Chart structure

```
helm/
├── rca-backend/
│   ├── Chart.yaml
│   ├── values.yaml              Default values
│   ├── values-prod.yaml         Production overrides (fill in before deploying)
│   └── templates/
│       ├── _helpers.tpl
│       ├── namespace.yaml
│       ├── serviceaccount.yaml  Workload Identity annotation
│       ├── configmap.yaml       Non-sensitive config (GCP project, model, CORS)
│       ├── secret.yaml          Credentials (created only if existingSecret not set)
│       ├── deployment.yaml
│       ├── service.yaml         ClusterIP
│       ├── hpa.yaml             HPA (2–10 replicas)
│       ├── ingress.yaml
│       └── NOTES.txt
└── rca-frontend/
    ├── Chart.yaml
    ├── values.yaml
    ├── values-prod.yaml
    └── templates/
        ├── _helpers.tpl
        ├── namespace.yaml
        ├── configmap.yaml       BACKEND_URL
        ├── deployment.yaml
        ├── service.yaml         ClusterIP
        ├── hpa.yaml             HPA (2–5 replicas)
        ├── ingress.yaml         GCE Ingress (public)
        └── NOTES.txt
```

---

## Prerequisites

```bash
# Tools needed
helm version          # v3+
kubectl version       # connected to your GKE cluster
gcloud auth login

# Enable APIs
gcloud services enable \
  aiplatform.googleapis.com \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  --project=YOUR_PROJECT_ID
```

---

## Step 1 — GCP setup (one-time)

```bash
PROJECT_ID=your-project-id
REGION=us-central1

# Create Artifact Registry
gcloud artifacts repositories create rca-agent \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID

# Create GCP service account for the backend
gcloud iam service-accounts create rca-agent-sa \
  --display-name="RCA Agent" \
  --project=$PROJECT_ID

# Grant Vertex AI access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:rca-agent-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Bind Workload Identity
gcloud iam service-accounts add-iam-policy-binding \
  rca-agent-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:$PROJECT_ID.svc.id.goog[rca-agent/rca-agent-sa]"

# Reserve a static IP for the ingress
gcloud compute addresses create rca-agent-ip \
  --global \
  --project=$PROJECT_ID
```

---

## Step 2 — Build and push images

```bash
# Build
docker build -f ../backend/Dockerfile  -t $REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-backend:latest  ../backend
docker build -f ../frontend/Dockerfile -t $REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-frontend:latest ../frontend

# Authenticate Docker to Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev

# Push
docker push $REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-backend:latest
docker push $REGION-docker.pkg.dev/$PROJECT_ID/rca-agent/rca-frontend:latest
```

---

## Step 3 — Create the credentials secret

Sensitive values (ServiceNow, Confluence) go into a K8s Secret — never into values files committed to git.

```bash
kubectl create namespace rca-agent   # if not already created

kubectl create secret generic rca-agent-secrets \
  --namespace=rca-agent \
  --from-literal=SERVICENOW_INSTANCE=https://myco.service-now.com \
  --from-literal=SERVICENOW_USERNAME=svc_rca_agent \
  --from-literal=SERVICENOW_PASSWORD=YOUR_PASSWORD \
  --from-literal=CONFLUENCE_BASE_URL=https://myco.atlassian.net/wiki \
  --from-literal=CONFLUENCE_USERNAME=sre@myco.com \
  --from-literal=CONFLUENCE_API_TOKEN=YOUR_API_TOKEN \
  --from-literal=CONFLUENCE_SPACE_KEY=SRE \
  --from-literal=CONFLUENCE_PARENT_PAGE_ID=123456789
```

---

## Step 4 — Edit values-prod.yaml files

Edit both `rca-backend/values-prod.yaml` and `rca-frontend/values-prod.yaml`.
Replace every `YOUR_PROJECT_ID` with your real GCP project ID.

---

## Step 5 — Install charts

```bash
# Install backend first (it creates the namespace)
helm upgrade --install rca-backend ./rca-backend \
  -f rca-backend/values-prod.yaml \
  --namespace rca-agent \
  --create-namespace \
  --wait

# Install frontend
helm upgrade --install rca-frontend ./rca-frontend \
  -f rca-frontend/values-prod.yaml \
  --namespace rca-agent \
  --wait
```

---

## Verify deployment

```bash
# Check pods
kubectl get pods -n rca-agent

# Check services
kubectl get svc -n rca-agent

# Check ingress (wait ~2 mins for GCE to assign an IP)
kubectl get ingress -n rca-agent

# Port-forward to test the backend locally
kubectl port-forward svc/rca-backend 8080:80 -n rca-agent

# Health check
curl http://localhost:8080/health | jq .

# Test ServiceNow fetch
curl http://localhost:8080/api/v1/rca/servicenow/INC0091847 | jq .

# Full end-to-end dry run
curl -s -X POST http://localhost:8080/api/v1/rca/from-servicenow \
  -H "Content-Type: application/json" \
  -d '{"incident_number":"INC0091847","publish_to_confluence":false}' | jq .
```

---

## Upgrade

```bash
# After a code change — rebuild image with new tag, then:
helm upgrade rca-backend ./rca-backend \
  -f rca-backend/values-prod.yaml \
  --namespace rca-agent \
  --set image.tag=v1.1.0

helm upgrade rca-frontend ./rca-frontend \
  -f rca-frontend/values-prod.yaml \
  --namespace rca-agent \
  --set image.tag=v1.1.0
```

---

## Rollback

```bash
# List history
helm history rca-backend -n rca-agent

# Roll back to previous release
helm rollback rca-backend -n rca-agent

# Roll back to a specific revision
helm rollback rca-backend 2 -n rca-agent
```

---

## Uninstall

```bash
helm uninstall rca-backend  -n rca-agent
helm uninstall rca-frontend -n rca-agent

# Delete the namespace (removes everything)
kubectl delete namespace rca-agent

# Delete the static IP (if you reserved one)
gcloud compute addresses delete rca-agent-ip --global --project=$PROJECT_ID
```

---

## Key values reference

### rca-backend

| Key | Default | Description |
|---|---|---|
| `image.repository` | `...rca-backend` | Artifact Registry image path |
| `image.tag` | `latest` | Image tag |
| `gcp.projectId` | `YOUR_PROJECT_ID` | GCP project |
| `gcp.geminiModel` | `gemini-1.5-pro` | Gemini model |
| `existingSecret` | `""` | Name of pre-created K8s Secret |
| `corsOrigins` | `http://localhost:8501` | Allowed frontend origins |
| `autoscaling.minReplicas` | `2` | Min pods |
| `autoscaling.maxReplicas` | `10` | Max pods |
| `serviceAccount.gcpServiceAccount` | `rca-agent-sa@...` | Workload Identity GCP SA |

### rca-frontend

| Key | Default | Description |
|---|---|---|
| `image.repository` | `...rca-frontend` | Artifact Registry image path |
| `backendUrl` | `http://rca-backend.rca-agent.svc.cluster.local` | Backend service URL |
| `ingress.enabled` | `true` | Enable GCE Ingress |
| `ingress.annotations` | `{}` | e.g. static IP name, managed cert |
| `autoscaling.minReplicas` | `2` | Min pods |
| `autoscaling.maxReplicas` | `5` | Max pods |
