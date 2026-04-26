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

# Build React app
FROM node:24-slim AS frontend-build
WORKDIR /app/frontend
# Upgrade npm to the desired version
RUN npm install -g npm@11.4.x
COPY frontend/ ./
RUN npm install
RUN npm run build

# Python backend
FROM python:3.12-slim
WORKDIR /app

# Install ffmpeg for audio conversion
RUN apt-get update && apt-get install -y wget tar ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask app
COPY *.py ./
COPY symptoms.json ./
COPY report_template.txt ./

# Copy built React app
COPY --from=frontend-build /app/frontend/build ./frontend/build
ENV FRONTEND_BUILD=/app/frontend/build

# Create cache directory and set permissions, then assign the env variable
RUN mkdir -p /cache && chmod 777 /cache
ENV CACHE_DIR=/cache

# If cache.zip exists, extract it into /cache
COPY cache* /tmp/
RUN if [ -f /tmp/cache_archive.zip ]; then \
      apt-get update && apt-get install -y unzip && \
      unzip /tmp/cache_archive.zip -d /cache && \
      rm /tmp/cache_archive.zip && \
      chmod -R 777 /cache; \
    fi

EXPOSE 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app", "--threads", "4", "--timeout", "300"]
