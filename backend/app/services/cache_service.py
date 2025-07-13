from diskcache import Cache
import os

# Create cache directory
cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
os.makedirs(cache_dir, exist_ok=True)

# Initialize cache
cache = Cache(cache_dir)