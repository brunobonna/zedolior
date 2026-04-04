import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_supabase, ADMIN_PASSWORD
from datetime import datetime, date, time

st.set_page_config(page_title="Viagens — Admin", page_icon="🗺️", layout="wide")

# Auth guard
if not st.session_state.get("authenticated"):
    st.warning("Faça login na página principal.")
    st.stop()

db = get_supabase()

# ── Helpers ───────────────────────────────────────────────────

def load_trips():
    return db.table("trips").select("*").order("departure_at").execute().data

def load_stops(trip_id: str):
    return db.table("trip_stops").select("*").eq("trip_id", trip_id).order("stop_order").execute().data

def confirmed_count(trip_id: str) -> int:
    rows = db.table("passengers").select("id").eq("trip_id", trip_id).execute().data
    return len(rows)

def cities_in_use(trip_id: str) -> set:
    rows = db.table("passengers").select("boarding_city, alighting_city").eq("trip_id", trip_id).execute().data
    cities = set()
    for r in rows:
        cities.add(r["boarding_city"])
        cities.add(r["alighting_city"])
    return cities

def save_stops(trip_id: str, cities: list[str]):
    db.table("trip_stops").delete().eq("trip_id", trip_id).execute()
    for i, city in enumerate(cities):
        if city.strip():
            db.table("trip_stops").insert({"trip_id": trip_id, "city": city.strip(), "stop_order": i}).execute()

def status_label(s: str) -> str:
    return {"active": "✅ Ativa", "cancelled": "❌ Cancelada", "completed": "🏁 Concluída"}.get(s, s)

def fmt_dt(dt_str: str | None) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str

# ── Trip form (create / edit) ─────────────────────────────────

def trip_form(trip: dict | None = None, key_prefix: str = "new"):
    """Renders trip form. Returns (submitted, form_data) tuple."""
    is_edit = trip is not None

    with st.form(key=f"trip_form_{key_prefix}"):
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("Cidade de origem *", value=trip["origin"] if is_edit else "")
        with col2:
            destination = st.text_input("Cidade de destino *", value=trip["destination"] if is_edit else "")

        st.markdown("**Paradas intermediárias** (ordem de parada; inclua origem e destino)")
        if is_edit:
            existing_stops = load_stops(trip["id"])
            default_stops = [s["city"] for s in existing_stops]
        else:
            default_stops = []

        # Up to 10 stops
        num_stops = st.number_input("Número de cidades (incluindo origem e destino)", min_value=2, max_value=10,
                                    value=max(2, len(default_stops)), step=1, key=f"nstops_{key_prefix}")
        stops = []
        for i in range(int(num_stops)):
            default_val = default_stops[i] if i < len(default_stops) else ""
            label = "Origem (1ª parada)" if i == 0 else (f"Destino ({i+1}ª parada)" if i == int(num_stops) - 1 else f"Parada {i+1}")
            stops.append(st.text_input(label, value=default_val, key=f"stop_{key_prefix}_{i}"))

        col3, col4 = st.columns(2)
        with col3:
            dep_date = st.date_input("Data de saída *",
                value=datetime.fromisoformat(trip["departure_at"]).date() if is_edit else date.today())
            dep_time = st.time_input("Horário de saída *",
                value=datetime.fromisoformat(trip["departure_at"]).time() if is_edit else time(6, 0))
        with col4:
            has_arrival = st.checkbox("Definir data/hora de chegada",
                value=bool(trip.get("arrival_at")) if is_edit else False)
            if has_arrival:
                arr_date = st.date_input("Data de chegada",
                    value=datetime.fromisoformat(trip["arrival_at"]).date() if (is_edit and trip.get("arrival_at")) else date.today())
                arr_time = st.time_input("Horário de chegada",
                    value=datetime.fromisoformat(trip["arrival_at"]).time() if (is_edit and trip.get("arrival_at")) else time(12, 0))
            else:
                arr_date, arr_time = None, None

        col5, col6 = st.columns(2)
        with col5:
            total_seats = st.number_input("Total de vagas *", min_value=1, max_value=100,
                value=trip["total_seats"] if is_edit else 8)
        with col6:
            price = st.number_input("Preço (R$) *", min_value=0.0, step=10.0, format="%.2f",
                value=float(trip["price"]) if is_edit else 0.0)

        if is_edit:
            status = st.selectbox("Status", ["active", "cancelled", "completed"],
                index=["active", "cancelled", "completed"].index(trip["status"]),
                format_func=status_label)
        else:
            status = "active"

        notes = st.text_area("Observações internas", value=trip.get("notes") or "" if is_edit else "")

        label = "💾 Salvar alterações" if is_edit else "➕ Criar viagem"
        submitted = st.form_submit_button(label, type="primary")

    if submitted:
        # Validations
        errors = []
        if not origin.strip():
            errors.append("Informe a cidade de origem.")
        if not destination.strip():
            errors.append("Informe a cidade de destino.")
        valid_stops = [s.strip() for s in stops if s.strip()]
        if len(valid_stops) < 2:
            errors.append("Informe pelo menos origem e destino nas paradas.")

        if is_edit:
            n_confirmed = confirmed_count(trip["id"])
            if total_seats < n_confirmed:
                errors.append(f"Não é possível reduzir para {int(total_seats)} vagas pois há {n_confirmed} passageiro(s) confirmado(s).")

            # Check if any stop was removed that has passengers
            old_cities = {s["city"] for s in load_stops(trip["id"])}
            new_cities = set(valid_stops)
            removed = old_cities - new_cities
            if removed:
                used = cities_in_use(trip["id"])
                blocked = removed & used
                if blocked:
                    errors.append(f"As cidades a seguir não podem ser removidas pois há passageiros embarcando ou desembarcando nelas: {', '.join(sorted(blocked))}.")

        if errors:
            for e in errors:
                st.error(e)
            return False, None

        departure_at = datetime.combine(dep_date, dep_time).isoformat()
        arrival_at = datetime.combine(arr_date, arr_time).isoformat() if has_arrival and arr_date else None

        form_data = {
            "origin": origin.strip(),
            "destination": destination.strip(),
            "departure_at": departure_at,
            "arrival_at": arrival_at,
            "total_seats": int(total_seats),
            "price": float(price),
            "status": status,
            "notes": notes.strip() or None,
        }
        return True, (form_data, valid_stops)

    return False, None

# ── Main UI ───────────────────────────────────────────────────

st.title("🗺️ Viagens")

# Create new trip
with st.expander("➕ Nova viagem", expanded=False):
    submitted, result = trip_form(key_prefix="new")
    if submitted and result:
        form_data, stops_list = result
        try:
            new_trip = db.table("trips").insert(form_data).execute().data[0]
            save_stops(new_trip["id"], stops_list)
            st.success("Viagem criada com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar viagem: {e}")

st.divider()

# Trip list
trips = load_trips()
if not trips:
    st.info("Nenhuma viagem cadastrada ainda. Crie a primeira viagem acima.")
    st.stop()

# Filter
filter_status = st.selectbox("Filtrar por status", ["Todas", "Ativas", "Canceladas", "Concluídas"])
status_map = {"Ativas": "active", "Canceladas": "cancelled", "Concluídas": "completed"}
if filter_status != "Todas":
    trips = [t for t in trips if t["status"] == status_map[filter_status]]

st.caption(f"{len(trips)} viagem(ns) encontrada(s)")

for trip in trips:
    stops = load_stops(trip["id"])
    stop_cities = " → ".join(s["city"] for s in stops) if stops else f"{trip['origin']} → {trip['destination']}"
    n_confirmed = confirmed_count(trip["id"])
    available = trip["total_seats"] - n_confirmed

    status_icon = {"active": "✅", "cancelled": "❌", "completed": "🏁"}.get(trip["status"], "")
    header = f"{status_icon} {trip['origin']} → {trip['destination']} | {fmt_dt(trip['departure_at'])} | {available}/{trip['total_seats']} vagas | R$ {float(trip['price']):.2f}"

    with st.expander(header):
        st.markdown(f"**Rota completa:** {stop_cities}")
        if trip.get("arrival_at"):
            st.markdown(f"**Chegada prevista:** {fmt_dt(trip['arrival_at'])}")
        if trip.get("notes"):
            st.markdown(f"**Observações:** {trip['notes']}")

        col_edit, col_cancel, col_complete = st.columns([2, 1, 1])
        with col_cancel:
            if trip["status"] == "active":
                if st.button("❌ Cancelar", key=f"cancel_{trip['id']}"):
                    db.table("trips").update({"status": "cancelled"}).eq("id", trip["id"]).execute()
                    st.rerun()
        with col_complete:
            if trip["status"] == "active":
                if st.button("🏁 Concluir", key=f"complete_{trip['id']}"):
                    db.table("trips").update({"status": "completed"}).eq("id", trip["id"]).execute()
                    st.rerun()

        # Edit form
        if f"edit_{trip['id']}" not in st.session_state:
            st.session_state[f"edit_{trip['id']}"] = False

        if st.button("✏️ Editar esta viagem", key=f"edit_btn_{trip['id']}"):
            st.session_state[f"edit_{trip['id']}"] = not st.session_state[f"edit_{trip['id']}"]
            st.rerun()

        if st.session_state.get(f"edit_{trip['id']}"):
            st.markdown("---")
            submitted, result = trip_form(trip=trip, key_prefix=trip["id"])
            if submitted and result:
                form_data, stops_list = result
                try:
                    db.table("trips").update(form_data).eq("id", trip["id"]).execute()
                    save_stops(trip["id"], stops_list)
                    st.session_state[f"edit_{trip['id']}"] = False
                    st.success("Viagem atualizada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
