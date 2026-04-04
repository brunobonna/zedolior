import streamlit as st
from supabase import create_client, Client

def _get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        import os
        return os.environ.get(key, default)

SUPABASE_URL: str = _get_secret("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = _get_secret("SUPABASE_SERVICE_KEY")
ADMIN_PASSWORD: str = _get_secret("ADMIN_PASSWORD")
WHATSAPP_NUMBER: str = _get_secret("WHATSAPP_NUMBER", "5521981695585")

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
