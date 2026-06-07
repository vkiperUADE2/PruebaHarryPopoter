import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from db.cassandra_client import get_cassandra


print(f"Connected to Astra DB: {get_cassandra().list_collection_names()}")
