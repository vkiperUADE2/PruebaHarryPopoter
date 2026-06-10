from supabase import create_client, Client
from config import SUPABASE_KEY, SUPABASE_URL

_client: Client | None = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
