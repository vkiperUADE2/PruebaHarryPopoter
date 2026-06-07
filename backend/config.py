import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).parent.parent / ".env")


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta configurar {name} en el archivo .env")
    return value


SUPABASE_URL = required("SUPABASE_URL")
SUPABASE_KEY = required("SUPABASE_KEY")
REDIS_HOST = required("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = required("REDIS_PASSWORD")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
MONGODB_URI = required("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "harry_potter")
ASTRA_DB_URL = required("ASTRA_DB_URL")
ASTRA_TOKEN = required("ASTRA_TOKEN")
