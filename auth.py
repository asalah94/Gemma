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

import json
import datetime
from google.oauth2 import service_account
import google.auth.transport.requests

def create_credentials(secret_key_json) -> service_account.Credentials:
  """Creates Google Cloud credentials from the provided service account key.

  Returns:
      service_account.Credentials: The created credentials object.

  Raises:
      ValueError: If the environment variable is not set or is empty, or if the
          JSON format is invalid.
  """

  if not secret_key_json:
    raise ValueError("Userdata variable 'GCP_MEDGEMMA_SERVICE_ACCOUNT_KEY' is not set or is empty.")
  try:
    service_account_info = json.loads(secret_key_json)
  except (SyntaxError, ValueError) as e:
    raise ValueError("Invalid service account key JSON format.") from e
  return service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
  )

def refresh_credentials(credentials: service_account.Credentials) -> service_account.Credentials:
  """Refreshes the provided Google Cloud credentials if they are about to expire
    (within 5 minutes) or if they don't have an expiry time set.

  Args:
      credentials: The credentials object to refresh.

  Returns:
      service_account.Credentials: The refreshed credentials object.
  """
  if credentials.expiry:
    expiry_time = credentials.expiry.replace(tzinfo=datetime.timezone.utc)
    # Calculate the time remaining until expiration
    time_remaining = expiry_time - datetime.datetime.now(datetime.timezone.utc)
    # Check if the token is about to expire (e.g., within 5 minutes)
    if time_remaining < datetime.timedelta(minutes=5):
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
  else:
    # If no expiry is set, always attempt to refresh (e.g., for certain credential types)
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
  return credentials

def get_access_token_refresh_if_needed(credentials: service_account.Credentials) -> str:
  """Gets the access token from the credentials, refreshing them if needed.

  Args:
      credentials: The credentials object.

  Returns:
      str: The access token.
  """
  credentials = refresh_credentials(credentials)
  return credentials.token

