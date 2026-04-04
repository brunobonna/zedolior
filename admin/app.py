import streamlit as st
from config import ADMIN_PASSWORD

st.set_page_config(
    page_title="Zé do Lior Viagens — Admin",
    page_icon="🚐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth gate ────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🚐 Zé do Lior Viagens")
        st.subheader("Painel Administrativo")
        st.divider()
        password = st.text_input("Senha de acesso", type="password", placeholder="Digite a senha...")
        if st.button("Entrar", use_container_width=True, type="primary"):
            if password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("🚐 Zé do Lior")
    st.caption("Painel Administrativo")
    st.divider()
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ── Página inicial ────────────────────────────────────────────
st.title("🚐 Zé do Lior Viagens")
st.write("Bem-vindo ao painel administrativo. Use o menu ao lado para navegar.")

# Resumo rápido
from config import get_supabase
try:
    db = get_supabase()
    trips = db.table("trips").select("id, status").execute().data
    active = sum(1 for t in trips if t["status"] == "active")
    pending = db.table("pending_requests").select("id").eq("status", "pending").execute().data

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Viagens ativas", active)
    with col2:
        st.metric("Total de viagens", len(trips))
    with col3:
        st.metric("Solicitações pendentes", len(pending))
except Exception as e:
    st.info("Configure as credenciais do Supabase em `.streamlit/secrets.toml` para conectar ao banco de dados.")
    st.caption(f"Detalhe: {e}")
