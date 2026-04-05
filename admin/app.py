import streamlit as st
from config import ADMIN_PASSWORD
from datetime import datetime

st.set_page_config(
    page_title="Painel — Zé do Lior",
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

# ── Navegação com labels customizados ─────────────────────────
painel     = st.Page("app_painel.py",      title="Painel",      icon="📊", default=True)
viagens    = st.Page("pages/1_Viagens.py",    title="Viagens",     icon="🗺️")
passageiros= st.Page("pages/2_Passageiros.py",title="Passageiros", icon="👥")
pendentes  = st.Page("pages/3_Pendentes.py",  title="Pendentes",   icon="📬")

pg = st.navigation([painel, viagens, passageiros, pendentes], position="sidebar")

with st.sidebar:
    st.title("🚐 Zé do Lior")
    st.caption("Painel Administrativo")
    st.divider()
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

pg.run()
