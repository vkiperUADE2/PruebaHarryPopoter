import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from db.redis_client import get_redis


print(f"Connected to Redis: {get_redis().ping()}")
