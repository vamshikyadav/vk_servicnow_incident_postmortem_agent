#!/bin/bash

# Root folder
PROJECT="vk_servicnow_incident_postmortem_agent"

echo "Creating project structure..."

# Create directories
mkdir -p $PROJECT/app/api
mkdir -p $PROJECT/app/agents
mkdir -p $PROJECT/app/services
mkdir -p $PROJECT/app/models
mkdir -p $PROJECT/app/templates
mkdir -p $PROJECT/app/utils
mkdir -p $PROJECT/tests

# Create main files
touch $PROJECT/app/main.py
touch $PROJECT/app/api/routes.py

# Agents
touch $PROJECT/app/agents/extractor_agent.py
touch $PROJECT/app/agents/classifier_agent.py
touch $PROJECT/app/agents/timeline_agent.py
touch $PROJECT/app/agents/validator_agent.py
touch $PROJECT/app/agents/writer_agent.py

# Services
touch $PROJECT/app/services/servicenow_client.py
touch $PROJECT/app/services/confluence_client.py
touch $PROJECT/app/services/timeline_service.py

# Models
touch $PROJECT/app/models/incident.py
touch $PROJECT/app/models/timeline.py
touch $PROJECT/app/models/postmortem.py

# Templates
touch $PROJECT/app/templates/confluence_template.md

# Utils
touch $PROJECT/app/utils/scoring.py
touch $PROJECT/app/utils/filtering.py
touch $PROJECT/app/utils/logging.py

# Root files
touch $PROJECT/Dockerfile
touch $PROJECT/requirements.txt

echo "✅ Project structure created successfully!"