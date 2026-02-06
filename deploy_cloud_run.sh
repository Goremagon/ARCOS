#!/bin/bash

# --- ARCOS DEPLOYMENT SCRIPT ---
# Deploys Auto-Agent and Maestro to Google Cloud Run with Redis backing.

# CONFIG
PROJECT_ID="your-project-id"
REGION="us-central1"
REDIS_NAME="arcos-redis"
NETWORK="default"

echo "🚀 Starting ARCOS Cloud Deployment..."

# 1. Enable APIs
echo "   🔧 Enabling Cloud Run & Redis APIs..."
gcloud services enable run.googleapis.com redis.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project=$PROJECT_ID

# 2. Provision Redis (Memorystore)
# NOTE: This takes ~15 minutes. Check if it exists first.
if ! gcloud redis instances describe $REDIS_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "   📦 Creating Redis Instance (Tier: BASIC, Size: 1GB)..."
    gcloud redis instances create $REDIS_NAME --size=1 --region=$REGION --project=$PROJECT_ID --network=$NETWORK
else
    echo "   ✅ Redis instance '$REDIS_NAME' already exists."
fi

# Get Redis Host/Port
REDIS_HOST=$(gcloud redis instances describe $REDIS_NAME --region=$REGION --project=$PROJECT_ID --format='value(host)')
REDIS_PORT=$(gcloud redis instances describe $REDIS_NAME --region=$REGION --project=$PROJECT_ID --format='value(port)')
REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT"

echo "   🔗 Redis Configuration: $REDIS_URL"

# 3. Create Artifact Repository (if needed)
REPO_NAME="arcos-repo"
if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    gcloud artifacts repositories create $REPO_NAME --repository-format=docker --location=$REGION --project=$PROJECT_ID
fi

# 4. Build & Deploy Maestro (Rust)
echo "   🧠 Deploying Maestro (Brain)..."
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/maestro --file Dockerfile.maestro .

gcloud run deploy arcos-maestro \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/maestro \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars "REDIS_URL=$REDIS_URL" \
    --no-cpu-throttling \
    --min-instances 1 \
    --max-instances 1 \
    --vpc-connector arcos-vpc-conn # OPTIONAL: Requires VPC Connector for Redis if not using Serverless VPC Access

# 5. Build & Deploy Agent (Python)
echo "   🕵️ Deploying Agent (Hunter)..."
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/agent --file Dockerfile.agent .

gcloud run deploy arcos-agent \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/agent \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars "REDIS_URL=$REDIS_URL" \
    --no-cpu-throttling \
    --min-instances 1 \
    --max-instances 1 \
    --vpc-connector arcos-vpc-conn # OPTIONAL

echo "✅ Deployment Complete! Check Cloud Run Console."
