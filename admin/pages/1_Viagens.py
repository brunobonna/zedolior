import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_supabase
from datetime import datetime, date, time

st.set_page_config(page_title="Viagens — Admin", page_icon="🗺️", layout="wide")

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
    return len(db.table("passengers").select("id").eq("trip_id", trip_id).execute().data)

def cities_in_use(trip_id: str) -> set:
    rows = db.table("passengers").select("boarding_city, alighting_city").eq("trip_id", trip_id).execute().data
    return {c for r in rows for c in (r["boarding_city"], r["alighting_city"])}

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
        return datetime.fromisoformat(dt_str).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str

def clear_form_state(sk: str):
    for k in [f"tf_origin_{sk}", f"tf_dest_{sk}", f"tf_inter_{sk}", f"tf_init_{sk}"]:
        st.session_state.pop(k, None)

# ── Stops editor (fora do st.form para ser reativo) ───────────

def stops_editor(sk: str, trip: dict | None = None):
    """
    Renderiza os campos de origem, destino e paradas intermediárias.
    Usa session_state para que +/- sejam imediatos sem aguardar submit.
    Retorna (origin, destination, all_stops_list) atuais.
    """
    # Inicializa session state apenas na primeira vez
    if not st.session_state.get(f"tf_init_{sk}"):
        if trip:
            existing = load_stops(trip["id"])
            cities = [s["city"] for s in existing]
            st.session_state[f"tf_origin_{sk}"] = trip["origin"]
            st.session_state[f"tf_dest_{sk}"]   = trip["destination"]
            # intermediárias = todas exceto primeira e última
            st.session_state[f"tf_inter_{sk}"]  = cities[1:-1] if len(cities) > 2 else []
        else:
            st.session_state[f"tf_origin_{sk}"] = ""
            st.session_state[f"tf_dest_{sk}"]   = ""
            st.session_state[f"tf_inter_{sk}"]  = []
        st.session_state[f"tf_init_{sk}"] = True

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Cidade de origem *", key=f"tf_origin_{sk}")
    with col2:
        st.text_input("Cidade de destino *", key=f"tf_dest_{sk}")

    inter: list = st.session_state[f"tf_inter_{sk}"]

    # Campos das paradas intermediárias
    if inter:
        st.markdown("**Paradas intermediárias:**")
        for i in range(len(inter)):
            new_val = st.text_input(
                f"Parada intermediária {i + 1}",
                value=inter[i],
                key=f"tf_stop_{sk}_{i}",
            )
            st.session_state[f"tf_inter_{sk}"][i] = new_val

    # Botões + e -
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("➕ Parada", key=f"add_stop_{sk}"):
            st.session_state[f"tf_inter_{sk}"].append("")
            st.rerun()
    with c2:
        if st.button("➖ Remover", key=f"rem_stop_{sk}", disabled=len(inter) == 0):
            st.session_state[f"tf_inter_{sk}"].pop()
            st.rerun()

    # Preview da rota
    origin = st.session_state.get(f"tf_origin_{sk}", "")
    dest   = st.session_state.get(f"tf_dest_{sk}", "")
    parts  = [origin] + [s for s in inter if s.strip()] + [dest]
    if origin and dest:
        st.caption("🗺️ Rota: " + " → ".join(p for p in parts if p))

    return origin, dest, parts

# ── Trip form (datas / vagas / preço dentro do st.form) ────────

def trip_form(sk: str, trip: dict | None = None):
    """
    Renderiza o formulário de viagem.
    As paradas ficam fora do st.form (reativas).
    Retorna (submitted, form_data, stops_list) ou (False, None, None).
    """
    is_edit = trip is not None

    origin, dest, all_stops = stops_editor(sk, trip)

    with st.form(key=f"trip_details_{sk}"):
        col3, col4 = st.columns(2)
        with col3:
            dep_date = st.date_input(
                "Data de saída *",
                value=datetime.fromisoformat(trip["departure_at"]).date() if is_edit else date.today(),
            )
            dep_time = st.time_input(
                "Horário de saída *",
                value=datetime.fromisoformat(trip["departure_at"]).time() if is_edit else time(6, 0),
            )
        with col4:
            has_arrival = st.checkbox(
                "Definir data/hora de chegada",
                value=bool(trip.get("arrival_at")) if is_edit else False,
            )
            if has_arrival:
                arr_date = st.date_input(
                    "Data de chegada",
                    value=datetime.fromisoformat(trip["arrival_at"]).date() if (is_edit and trip.get("arrival_at")) else date.today(),
                )
                arr_time = st.time_input(
                    "Horário de chegada",
                    value=datetime.fromisoformat(trip["arrival_at"]).time() if (is_edit and trip.get("arrival_at")) else time(12, 0),
                )
            else:
                arr_date = arr_time = None

        col5, col6 = st.columns(2)
        with col5:
            total_seats = st.number_input(
                "Total de vagas *", min_value=1, max_value=200,
                value=trip["total_seats"] if is_edit else 40,
            )
        with col6:
            price = st.number_input(
                "Preço (R$) *", min_value=0.0, step=10.0, format="%.2f",
                value=float(trip["price"]) if is_edit else 0.0,
            )

        if is_edit:
            status = st.selectbox(
                "Status", ["active", "cancelled", "completed"],
                index=["active", "cancelled", "completed"].index(trip["status"]),
                format_func=status_label,
            )
        else:
            status = "active"

        notes = st.text_area("Observações internas (só visível no admin)",
            value=trip.get("notes") or "" if is_edit else "")
        public_notes = st.text_area("Observações públicas (aparece no site para os clientes)",
            value=trip.get("public_notes") or "" if is_edit else "")

        label = "💾 Salvar alterações" if is_edit else "➕ Criar viagem"
        submitted = st.form_submit_button(label, type="primary")

    if submitted:
        errors = []
        if not origin.strip():
            errors.append("Informe a cidade de origem.")
        if not dest.strip():
            errors.append("Informe a cidade de destino.")
        valid_stops = [s.strip() for s in all_stops if s.strip()]
        if len(valid_stops) < 2:
            errors.append("Origem e destino são obrigatórios.")

        if is_edit:
            n_conf = confirmed_count(trip["id"])
            if int(total_seats) < n_conf:
                errors.append(f"Não é possível reduzir para {int(total_seats)} vagas — há {n_conf} passageiro(s) confirmado(s).")
            old_cities = {s["city"] for s in load_stops(trip["id"])}
            removed = old_cities - set(valid_stops)
            if removed:
                blocked = removed & cities_in_use(trip["id"])
                if blocked:
                    errors.append(f"Cidades com passageiros, não podem ser removidas: {', '.join(sorted(blocked))}.")

        if errors:
            for e in errors:
                st.error(e)
            return False, None, None

        form_data = {
            "origin": origin.strip(),
            "destination": dest.strip(),
            "departure_at": datetime.combine(dep_date, dep_time).isoformat(),
            "arrival_at": datetime.combine(arr_date, arr_time).isoformat() if has_arrival and arr_date else None,
            "total_seats": int(total_seats),
            "price": float(price),
            "status": status,
            "notes": notes.strip() or None,
            "public_notes": public_notes.strip() or None,
        }
        return True, form_data, valid_stops

    return False, None, None

# ── Main UI ───────────────────────────────────────────────────

st.title("🗺️ Viagens")

# ── Nova viagem ───────────────────────────────────────────────
with st.expander("➕ Nova viagem", expanded=False):
    submitted, form_data, stops_list = trip_form("new")
    if submitted and form_data:
        try:
            new_trip = db.table("trips").insert(form_data).execute().data[0]
            save_stops(new_trip["id"], stops_list)
            clear_form_state("new")
            st.success("Viagem criada com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar viagem: {e}")

st.divider()

# ── Lista de viagens ──────────────────────────────────────────
trips = load_trips()
if not trips:
    st.info("Nenhuma viagem cadastrada ainda. Crie a primeira viagem acima.")
    st.stop()

# Filtro — padrão: Ativas
filter_status = st.selectbox(
    "Filtrar por status",
    ["Ativas", "Todas", "Canceladas", "Concluídas"],
)
status_map = {"Ativas": "active", "Canceladas": "cancelled", "Concluídas": "completed"}
if filter_status != "Todas":
    trips = [t for t in trips if t["status"] == status_map[filter_status]]

st.caption(f"{len(trips)} viagem(ns) encontrada(s)")

# Carrega passageiros e pendentes de todas as viagens visíveis em batch
trip_ids = [t["id"] for t in trips]
all_pax = db.table("passengers").select("id, trip_id, name, seat_status, created_at").in_("trip_id", trip_ids).order("created_at").execute().data if trip_ids else []
all_pending = db.table("pending_requests").select("id, trip_id, passengers_json, submitted_at").eq("status", "pending").in_("trip_id", trip_ids).order("submitted_at").execute().data if trip_ids else []

def pax_for_trip(tid):
    paid = [p for p in all_pax if p["trip_id"] == tid and p["seat_status"] == "paid"]
    reserved = [p for p in all_pax if p["trip_id"] == tid and p["seat_status"] == "reserved"]
    pending_reqs = [r for r in all_pending if r["trip_id"] == tid]
    # Expande nomes dos pendentes
    pending_names = []
    for req in pending_reqs:
        for p in (req.get("passengers_json") or []):
            pending_names.append(p.get("name", "?"))
    return paid, reserved, pending_names

for trip in trips:
    stops       = load_stops(trip["id"])
    stop_cities = " → ".join(s["city"] for s in stops) if stops else f"{trip['origin']} → {trip['destination']}"
    n_confirmed = confirmed_count(trip["id"])
    available   = trip["total_seats"] - n_confirmed

    status_icon = {"active": "✅", "cancelled": "❌", "completed": "🏁"}.get(trip["status"], "")
    header = (
        f"{status_icon} {trip['origin']} → {trip['destination']} | "
        f"{fmt_dt(trip['departure_at'])} | "
        f"{available}/{trip['total_seats']} vagas | "
        f"R$ {float(trip['price']):.2f}"
    )

    paid_pax, reserved_pax, pending_names = pax_for_trip(trip["id"])

    with st.expander(header):
        st.markdown(f"**Rota completa:** {stop_cities}")
        if trip.get("arrival_at"):
            st.markdown(f"**Chegada prevista:** {fmt_dt(trip['arrival_at'])}")
        if trip.get("notes"):
            st.markdown(f"**Obs. internas:** {trip['notes']}")
        if trip.get("public_notes"):
            st.markdown(f"**Obs. públicas:** {trip['public_notes']}")

        # ── Lista de passageiros ──────────────────────────────
        total_listed = len(paid_pax) + len(reserved_pax) + len(pending_names)
        if total_listed:
            st.markdown("**Passageiros:**")
            lines = []
            n = 1
            for p in paid_pax:
                lines.append(f"{n}. ✅ {p['name']}")
                n += 1
            for p in reserved_pax:
                lines.append(f"{n}. ⏳ {p['name']}")
                n += 1
            for name in pending_names:
                lines.append(f"{n}. 🔔 {name} *(pendente)*")
                n += 1
            st.markdown("\n".join(lines))

        col_edit, col_cancel, col_complete = st.columns([2, 1, 1])
        with col_cancel:
            if trip["status"] == "active":
                if st.button("❌ Cancelar", key=f"cancel_{trip['id']}"):
                    st.session_state[f"confirm_cancel_{trip['id']}"] = True
                    st.rerun()
        with col_complete:
            if trip["status"] == "active":
                if st.button("🏁 Concluir", key=f"complete_{trip['id']}"):
                    st.session_state[f"confirm_complete_{trip['id']}"] = True
                    st.rerun()

        # Confirmação de cancelamento
        if st.session_state.get(f"confirm_cancel_{trip['id']}"):
            pax = db.table("passengers").select("seat_status").eq("trip_id", trip["id"]).execute().data
            n_paid = sum(1 for p in pax if p["seat_status"] == "paid")
            n_res  = sum(1 for p in pax if p["seat_status"] == "reserved")
            st.warning(
                f"⚠️ **Confirmar cancelamento?**\n\n"
                f"Esta viagem tem **{n_paid} passageiro(s) pago(s)** e "
                f"**{n_res} reservado(s)**. "
                f"O cancelamento não exclui os passageiros — você precisará contatá-los manualmente."
            )
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ Sim, cancelar", key=f"cancel_yes_{trip['id']}", type="primary"):
                    db.table("trips").update({"status": "cancelled"}).eq("id", trip["id"]).execute()
                    st.session_state.pop(f"confirm_cancel_{trip['id']}", None)
                    st.rerun()
            with cc2:
                if st.button("Voltar", key=f"cancel_no_{trip['id']}"):
                    st.session_state.pop(f"confirm_cancel_{trip['id']}", None)
                    st.rerun()

        # Confirmação de conclusão
        if st.session_state.get(f"confirm_complete_{trip['id']}"):
            st.info(f"🏁 **Confirmar conclusão?** A viagem será marcada como encerrada e não aparecerá mais no site público.")
            ce1, ce2 = st.columns(2)
            with ce1:
                if st.button("✅ Sim, concluir", key=f"complete_yes_{trip['id']}", type="primary"):
                    db.table("trips").update({"status": "completed"}).eq("id", trip["id"]).execute()
                    st.session_state.pop(f"confirm_complete_{trip['id']}", None)
                    st.rerun()
            with ce2:
                if st.button("Voltar", key=f"complete_no_{trip['id']}"):
                    st.session_state.pop(f"confirm_complete_{trip['id']}", None)
                    st.rerun()

        edit_key = f"edit_{trip['id']}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        if st.button("✏️ Editar esta viagem", key=f"edit_btn_{trip['id']}"):
            if st.session_state[edit_key]:
                # Fechar e limpar estado
                clear_form_state(trip["id"])
                st.session_state[edit_key] = False
            else:
                st.session_state[edit_key] = True
            st.rerun()

        if st.session_state.get(edit_key):
            st.markdown("---")
            submitted, form_data, stops_list = trip_form(trip["id"], trip=trip)
            if submitted and form_data:
                try:
                    db.table("trips").update(form_data).eq("id", trip["id"]).execute()
                    save_stops(trip["id"], stops_list)
                    clear_form_state(trip["id"])
                    st.session_state[edit_key] = False
                    st.success("Viagem atualizada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
