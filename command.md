# Check both are running
docker ps

# Logs
docker logs -f rca-backend
docker logs -f rca-frontend

# Stop and remove
docker stop rca-backend rca-frontend
docker rm rca-backend rca-frontend

# Rebuild just one (e.g. after a code change)

```
docker build -f backend/Dockerfile -t rca-backend:latest ./backend
docker stop rca-backend && docker rm rca-backend
docker run -d --name rca-backend -p 8080:8080 --env-file backend.env \
  -v "$HOME/.config/gcloud:/tmp/gcloud:ro" rca-backend:latest
```
```
# Backend (mount gcloud ADC credentials for local auth)
docker run -d \
  --name rca-backend \
  -p 8080:8080 \
  --env-file backend.env \
  -v "$HOME/.config/gcloud:/tmp/gcloud:ro" \
  rca-backend:latest

# Frontend
docker run -d \
  --name rca-frontend \
  -p 3000:80 \
  --env-file frontend.env \
  rca-frontend:latest
```