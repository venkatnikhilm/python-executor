#!/bin/bash
# GCP Cloud Run deployment script

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
SERVICE_NAME="secure-code-executor"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Building Docker image..."
docker build -t ${IMAGE_NAME} .

echo "Pushing image to GCR..."
docker push ${IMAGE_NAME}

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 30s \
  --max-instances 10

echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)'
