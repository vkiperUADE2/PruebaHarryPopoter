import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from db.supabase_client import get_supabase


roles = get_supabase().table("roles").select("id").execute().data
print(f"Connected to Supabase: {len(roles)} roles")
