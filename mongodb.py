import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from db.mongo_client import get_mongo


get_mongo().client.admin.command("ping")
print("Connected to MongoDB")
