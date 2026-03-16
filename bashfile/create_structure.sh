#!/bin/bash

PROJECT="vk_servicnow_incident_postmortem_agent"

echo "Creating project structure for $PROJECT..."

# Create directories
mkdir -p $PROJECT/app/api
mkdir -p $PROJECT/app/clients
mkdir -p $PROJECT/app/models
mkdir -p $PROJECT/app/services
mkdir -p $PROJECT/tests

# Core app files
touch $PROJECT/app/main.py
touch $PROJECT/app/config.py

# API
touch $PROJECT/app/api/routes.py

# Clients
touch $PROJECT/app/clients/servicenow_client.py
touch $PROJECT/app/clients/confluence_client.py
touch $PROJECT/app/clients/vertex_client.py

# Models
touch $PROJECT/app/models/incident.py
touch $PROJECT/app/models/events.py
touch $PROJECT/app/models/postmortem.py

# Services
touch $PROJECT/app/services/extractor_service.py
touch $PROJECT/app/services/filter_service.py
touch $PROJECT/app/services/timeline_service.py
touch $PROJECT/app/services/eureka_service.py
touch $PROJECT/app/services/publisher_service.py
touch $PROJECT/app/services/writer_service.py

# Root files
touch $PROJECT/requirements.txt
touch $PROJECT/Dockerfile

echo "✅ Project structure created successfully!"