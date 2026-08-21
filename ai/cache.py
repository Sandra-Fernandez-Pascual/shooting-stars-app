"""In-process TTL cache for lookups.

Uses functools instead of st.cache_data so the app can import without
pyarrow or Streamlit commands running before set_page_config.
"""

import time
from functools import lru_cache, wraps


def ttl_cache(seconds, maxsize=128):
    """Reuse a function result for `seconds` on this server."""

    def decorator(fn):
        @lru_cache(maxsize=maxsize)
        def cached(bucket, *args, **kwargs):
            return fn(*args, **kwargs)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            bucket = int(time.time() // seconds)
            return cached(bucket, *args, **kwargs)

        wrapper.cache_clear = cached.cache_clear
        return wrapper

    return decorator
