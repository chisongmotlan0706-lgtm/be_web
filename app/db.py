from supabase import Client, create_client

from app.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_KEY. "
            "Please create .env file from .env.example."
        )
    return create_client(settings.supabase_url, settings.supabase_key)
