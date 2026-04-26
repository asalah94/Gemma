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

try:
    from diskcache import Cache  # type: ignore
except Exception:
    Cache = None

import os
import shutil
import tempfile
import zipfile
import logging


# Provide a lightweight in-memory Cache fallback when `diskcache` is not installed.
class _InMemoryCache:
    def __init__(self, directory=None):
        self._store = {}

    def __len__(self):
        return len(self._store)

    def volume(self):
        # Approximate size in bytes
        try:
            return sum(len(str(v)) for v in self._store.values())
        except Exception:
            return 0

    def get(self, key, default=None):
        return self._store.get(key, default)

    def __setitem__(self, key, value):
        self._store[key] = value

    def __getitem__(self, key):
        return self._store[key]

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def memoize(self):
        def _decorator(func):
            cache_store = self._store

            def _make_key(*args, **kwargs):
                try:
                    return (func.__name__, args, tuple(sorted(kwargs.items())))
                except Exception:
                    return (func.__name__, str(args), str(kwargs))

            def wrapper(*args, **kwargs):
                key = _make_key(*args, **kwargs)
                if key in cache_store:
                    return cache_store[key]
                result = func(*args, **kwargs)
                cache_store[key] = result
                return result

            # Expose a simple __cache_key__ used elsewhere
            def __cache_key__inner(*a, **k):
                return _make_key(*a, **k)

            wrapper.__cache_key__ = __cache_key__inner
            return wrapper

        return _decorator


# Choose real disk-backed cache when available, otherwise fallback
if Cache is not None:
    cache = Cache(os.environ.get("CACHE_DIR", "/cache"))
else:
    logging.warning("diskcache not installed — using in-memory cache fallback")
    cache = _InMemoryCache(os.environ.get("CACHE_DIR", None))

# Print cache statistics after loading
try:
    item_count = len(cache)
    size_bytes = cache.volume()
    print(f"Cache loaded: {item_count} items, approx {size_bytes} bytes")
except Exception as e:
    print(f"Could not retrieve cache statistics: {e}")

def create_cache_zip():
    temp_dir = tempfile.gettempdir()
    base_name = os.path.join(temp_dir, "cache_archive") # A more descriptive name
    archive_path = base_name + ".zip"
    cache_directory = os.environ.get("CACHE_DIR", "/cache")
    
    if not os.path.isdir(cache_directory):
        logging.error(f"Cache directory not found at {cache_directory}")
        return None, f"Cache directory not found on server: {cache_directory}"
    
    logging.info("Forcing a cache checkpoint for safe backup...")
    try:
        # Open and immediately close a connection.
        # This forces SQLite to perform a checkpoint, merging the .wal file
        # into the main .db file, ensuring the on-disk files are consistent.
        with Cache(cache_directory) as temp_cache:
            temp_cache.close()
        
        # Clean up temporary files before archiving.
        tmp_path = os.path.join(cache_directory, 'tmp')
        if os.path.isdir(tmp_path):
            logging.info(f"Removing temporary cache directory: {tmp_path}")
            shutil.rmtree(tmp_path)

        logging.info(f"Checkpoint complete. Creating zip archive of {cache_directory} to {archive_path}")
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
            for root, _, files in os.walk(cache_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, cache_directory)
                    zipf.write(file_path, arcname)
        logging.info("Zip archive created successfully.")
        return archive_path, None
        
    except Exception as e:
        logging.error(f"Error creating zip archive of cache directory: {e}", exc_info=True)
        return None, f"Error creating zip archive: {e}"
