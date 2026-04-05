import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_supabase
from datetime import datetime, date

st.set_page_config(page_title="Passageiros — Admin", page_icon="👥", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Faça login na página principal.")
    st.stop()

db = get_supabase()

# ── Helpers ───────────────────────────────────────────────────

def load_active_trips():
    return db.table("trips").select("id, origin, destination, departure_at, total_seats, status").neq("status", "cancelled").order("departure_at").execute().data

def load_passengers(trip_id: str):
    return db.table("passengers").select("*").eq("trip_id", trip_id).order("created_at").execute().data

def load_stops(trip_id: str) -> list[str]:
    rows = db.table("trip_stops").select("city").eq("trip_id", trip_id).order("stop_order").execute().data
    return [r["city"] for r in rows]

def fmt_dt(dt_str: str | None) -> str:
    if not dt_str:
        return "—"
    try:
        return datetime.fromisoformat(dt_str).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str

def is_minor(birth_date_str: str) -> bool:
    try:
        bd = date.fromisoformat(birth_date_str)
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        return age < 18
    except Exception:
        return False

STATUS_OPTIONS = ["reserved", "paid"]
STATUS_LABELS = {"reserved": "⏳ Reservado", "paid": "✅ Pago"}
STATUS_COLORS = {"reserved": "🟡", "paid": "🟢"}

def passenger_form(stops: list[str], passenger: dict | None = None, key_prefix: str = "new_p"):
    """Renders passenger form. Returns (submitted, data) or (False, None)."""
    is_edit = passenger is not None

    with st.form(key=f"passenger_form_{key_prefix}"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome completo *", value=passenger["name"] if is_edit else "")
            cpf = st.text_input("CPF *", value=passenger["cpf"] if is_edit else "",
                                placeholder="000.000.000-00")
        with col2:
            rg = st.text_input("RG", value=passenger.get("rg") or "" if is_edit else "")
            birth_date = st.date_input("Data de nascimento *",
                value=date.fromisoformat(passenger["birth_date"]) if is_edit else date(1990, 1, 1),
                min_value=date(1900, 1, 1), max_value=date.today())

        # Embarque: qualquer cidade EXCETO o destino final (última parada)
        # Desembarque: qualquer cidade EXCETO a origem (primeira parada)
        boarding_options  = stops[:-1] if len(stops) > 1 else stops
        alighting_options = stops[1:]  if len(stops) > 1 else stops

        col3, col4 = st.columns(2)
        with col3:
            boarding_def = passenger["boarding_city"] if (is_edit and passenger["boarding_city"] in boarding_options) else boarding_options[0]
            boarding_city = st.selectbox("Cidade de embarque *", options=boarding_options,
                index=boarding_options.index(boarding_def))
        with col4:
            alighting_def = passenger["alighting_city"] if (is_edit and passenger["alighting_city"] in alighting_options) else alighting_options[-1]
            alighting_city = st.selectbox("Cidade de desembarque *", options=alighting_options,
                index=alighting_options.index(alighting_def))

        col5, col6 = st.columns(2)
        with col5:
            if is_edit:
                status_idx = STATUS_OPTIONS.index(passenger["seat_status"]) if passenger["seat_status"] in STATUS_OPTIONS else 0
                seat_status = st.selectbox("Status da vaga", STATUS_OPTIONS, index=status_idx,
                    format_func=lambda s: STATUS_LABELS.get(s, s))
            else:
                seat_status = st.selectbox("Status da vaga", STATUS_OPTIONS,
                    format_func=lambda s: STATUS_LABELS.get(s, s))
        with col6:
            notes = st.text_area("Observações (bagagem, etc.)",
                value=passenger.get("notes") or "" if is_edit else "", height=80)

        label = "💾 Salvar" if is_edit else "➕ Adicionar passageiro"
        submitted = st.form_submit_button(label, type="primary")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Informe o nome.")
        if not cpf.strip():
            errors.append("Informe o CPF.")
        if boarding_city == alighting_city:
            errors.append("Embarque e desembarque não podem ser na mesma cidade.")
        for e in errors:
            st.error(e)
        if errors:
            return False, None

        return True, {
            "name": name.strip(),
            "cpf": cpf.strip(),
            "rg": rg.strip() or None,
            "birth_date": birth_date.isoformat(),
            "is_minor": is_minor(birth_date.isoformat()),
            "boarding_city": boarding_city,
            "alighting_city": alighting_city,
            "seat_status": seat_status,
            "notes": notes.strip() or None,
        }

    return False, None

# ── Main UI ───────────────────────────────────────────────────

st.title("👥 Passageiros")

trips = load_active_trips()
if not trips:
    st.info("Nenhuma viagem ativa. Cadastre viagens na aba Viagens.")
    st.stop()

trip_options = {t["id"]: f"{t['origin']} → {t['destination']} | {fmt_dt(t['departure_at'])}" for t in trips}
selected_id = st.selectbox("Selecione a viagem", options=list(trip_options.keys()),
    format_func=lambda x: trip_options[x])

if not selected_id:
    st.stop()

passengers = load_passengers(selected_id)
stops = load_stops(selected_id)
trip = next(t for t in trips if t["id"] == selected_id)

n_paid     = sum(1 for p in passengers if p["seat_status"] == "paid")
n_reserved = sum(1 for p in passengers if p["seat_status"] == "reserved")
n_pending  = len(db.table("pending_requests").select("id").eq("trip_id", selected_id).eq("status", "pending").execute().data)
available  = trip["total_seats"] - len(passengers)

# Metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Vagas", trip["total_seats"])
col2.metric("Disponíveis", available)
col3.metric("✅ Pagos", n_paid)
col4.metric("⏳ Reservados", n_reserved)
col5.metric("🔔 Pendentes", n_pending)

st.divider()

# Add passenger
with st.expander("➕ Adicionar passageiro", expanded=False):
    if available <= 0:
        st.warning("Não há vagas disponíveis nesta viagem.")
    else:
        submitted, data = passenger_form(stops, key_prefix=f"new_{selected_id}")
        if submitted and data:
            data["trip_id"] = selected_id
            data["source"] = "admin"
            try:
                db.table("passengers").insert(data).execute()
                st.success("Passageiro adicionado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

st.divider()

# Passenger list
if not passengers:
    st.info("Nenhum passageiro cadastrado nesta viagem ainda.")
    st.stop()

# CSS for status badges
st.markdown("""
<style>
.badge-paid   { background:#d4edda; color:#155724; padding:2px 8px; border-radius:10px; font-size:0.85em; }
.badge-reserved { background:#fff3cd; color:#856404; padding:2px 8px; border-radius:10px; font-size:0.85em; }
.badge-minor  { background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:10px; font-size:0.85em; }
</style>
""", unsafe_allow_html=True)

st.subheader(f"Passageiros ({len(passengers)})")

for p in passengers:
    minor_badge = ' <span class="badge-minor">Menor</span>' if p.get("is_minor") else ""
    status_badge_class = "badge-paid" if p["seat_status"] == "paid" else "badge-reserved"
    status_text = STATUS_LABELS.get(p["seat_status"], p["seat_status"])
    header_html = f'<b>{p["name"]}</b>{minor_badge} &nbsp; <span class="{status_badge_class}">{status_text}</span>'

    with st.expander(f"{STATUS_COLORS.get(p['seat_status'], '')} {p['name']}", expanded=False):
        st.markdown(header_html, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**CPF:** {p['cpf']}")
            st.markdown(f"**RG:** {p.get('rg') or '—'}")
            st.markdown(f"**Nascimento:** {p['birth_date']}" + (" *(menor de idade)*" if p.get("is_minor") else ""))
        with col_b:
            st.markdown(f"**Embarque:** {p['boarding_city']}")
            st.markdown(f"**Desembarque:** {p['alighting_city']}")
            if p.get("notes"):
                st.markdown(f"**Obs:** {p['notes']}")

        # Status salvo automaticamente ao mudar
        def _make_status_saver(pid, old_status):
            def _save():
                new = st.session_state[f"status_{pid}"]
                if new != old_status:
                    db.table("passengers").update({"seat_status": new}).eq("id", pid).execute()
            return _save

        st.selectbox(
            "Status da vaga",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(p["seat_status"]) if p["seat_status"] in STATUS_OPTIONS else 0,
            format_func=lambda s: STATUS_LABELS.get(s, s),
            key=f"status_{p['id']}",
            on_change=_make_status_saver(p["id"], p["seat_status"]),
        )

        col_edit, col_del = st.columns([3, 1])
        with col_edit:
            edit_key = f"edit_p_{p['id']}"
            if st.button("✏️ Editar dados", key=f"edit_btn_{p['id']}"):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()

        with col_del:
            del_key = f"del_confirm_{p['id']}"
            if st.button("🗑️ Remover", key=f"del_btn_{p['id']}", type="secondary"):
                st.session_state[del_key] = True
                st.rerun()

        if st.session_state.get(f"del_confirm_{p['id']}"):
            st.warning(f"⚠️ Confirmar remoção de **{p['name']}**? Esta ação não pode ser desfeita.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Sim, remover", key=f"del_yes_{p['id']}", type="primary"):
                    db.table("passengers").delete().eq("id", p["id"]).execute()
                    st.session_state.pop(f"del_confirm_{p['id']}", None)
                    st.success("Passageiro removido.")
                    st.rerun()
            with c2:
                if st.button("Cancelar", key=f"del_no_{p['id']}"):
                    st.session_state.pop(f"del_confirm_{p['id']}", None)
                    st.rerun()

        if st.session_state.get(f"edit_p_{p['id']}"):
            st.markdown("---")
            submitted, data = passenger_form(stops, passenger=p, key_prefix=f"edit_{p['id']}")
            if submitted and data:
                try:
                    db.table("passengers").update(data).eq("id", p["id"]).execute()
                    st.session_state.pop(f"edit_p_{p['id']}", None)
                    st.success("Dados atualizados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
