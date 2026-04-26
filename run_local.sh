#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e
APP_NAME="appoint-ready"
HOST_APP_DIR="$(pwd)"
CONTAINER_APP_DIR="/app"

# Build the Docker image
echo "Building Docker image..."
docker build -t $APP_NAME .

# Check if the build was successful
if [ $? -ne 0 ]; then
  echo "Docker build failed!"
  exit 1
fi

# Run the Docker container with a volume and load environment variables from appoint-ready.env
echo "Running Docker container with env variables from appoint-ready.env..."
docker run -it --rm \
  --env-file ~/appoint-ready.env \
  -p 7860:7860 \
  --name "$APP_NAME" \
  $APP_NAME

# The script will block here until the container exits.
echo "Docker container has exited."
if grep -q "Could not find a required file." docker.log 2>/dev/null; then
  echo "WARNING: Build failed due to missing index.html in /app/frontend/public."
  echo "Please ensure that frontend/public/index.html exists before building."
fi
# Container removal is handled automatically by the '--rm' flag.
