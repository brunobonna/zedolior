import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_supabase
from datetime import datetime, date

st.set_page_config(page_title="Pendentes — Admin", page_icon="📬", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Faça login na página principal.")
    st.stop()

db = get_supabase()

# ── Helpers ───────────────────────────────────────────────────

def load_requests(status: str):
    # Só mostra pendentes de viagens ativas
    rows = (db.table("pending_requests")
              .select("*, trips(origin, destination, departure_at, status)")
              .eq("status", status)
              .order("submitted_at", desc=(status == "pending"))
              .execute().data)
    if status == "pending":
        rows = [r for r in rows if (r.get("trips") or {}).get("status") == "active"]
    return rows

def load_stops(trip_id: str) -> list[str]:
    rows = db.table("trip_stops").select("city").eq("trip_id", trip_id).order("stop_order").execute().data
    return [r["city"] for r in rows]

def load_seats(trip_ids: list[str]) -> dict:
    if not trip_ids:
        return {}
    rows = db.table("trip_availability").select("id, total_seats, seats_taken").in_("id", trip_ids).execute().data
    return {r["id"]: r for r in rows}

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

def is_toddler(birth_date_str: str) -> bool:
    try:
        bd = date.fromisoformat(birth_date_str)
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        return age < 7
    except Exception:
        return False

# ── Main UI ───────────────────────────────────────────────────

st.title("📬 Solicitações Pendentes")

# Count badge
pending_count = len(db.table("pending_requests").select("id").eq("status", "pending").execute().data)
st.caption(f"{'🔴 ' if pending_count > 0 else ''}Aguardando aprovação: **{pending_count}** solicitação(ões)")

tab_pending, tab_approved, tab_rejected = st.tabs([
    f"⏳ Pendentes ({pending_count})",
    "✅ Aprovados",
    "❌ Rejeitados",
])

# ── Tab: Pendentes ────────────────────────────────────────────
with tab_pending:
    requests = load_requests("pending")
    if not requests:
        st.info("Nenhuma solicitação pendente no momento.")
    else:
        trip_ids_pend = list({r["trip_id"] for r in requests})
        seats_pend = load_seats(trip_ids_pend)
        for req in requests:
            trip_info = req.get("trips", {}) or {}
            seats = seats_pend.get(req["trip_id"], {})
            seats_str = f" | {seats.get('seats_taken', '?')}/{seats.get('total_seats', '?')} ocupadas" if seats else ""
            trip_label = f"{trip_info.get('origin', '?')} → {trip_info.get('destination', '?')} | {fmt_dt(trip_info.get('departure_at'))}{seats_str}"
            stops = load_stops(req["trip_id"])
            passengers_json = req.get("passengers_json") or []
            first_name = passengers_json[0].get("name", "?") if passengers_json else "?"
            n_pass = req["passenger_count"]
            extra = f" +{n_pass - 1} mais" if n_pass > 1 else ""
            with st.expander(f"📋 {first_name}{extra} | {trip_label} | {fmt_dt(req['submitted_at'])}", expanded=True):
                st.markdown(f"**Viagem:** {trip_label}")
                st.markdown(f"**Embarque:** {req['boarding_city']} &nbsp;→&nbsp; **Desembarque:** {req['alighting_city']}")
                st.markdown(f"**Enviado em:** {fmt_dt(req['submitted_at'])}")

                # Botões WhatsApp por passageiro (fora do form)
                for i, p_raw in enumerate(passengers_json):
                    raw_phone = p_raw.get("phone", "")
                    if raw_phone:
                        digits = "".join(c for c in raw_phone if c.isdigit())
                        wa = f"https://wa.me/55{digits}" if not digits.startswith("55") else f"https://wa.me/{digits}"
                        label = p_raw.get("name") or f"Passageiro {i+1}"
                        st.link_button(f"💬 WhatsApp — {label} ({raw_phone})", wa)

                st.divider()

                # ── Approval form (editable) ──────────────────
                approve_key = f"approve_{req['id']}"
                if st.button("✅ Aprovar / Editar e confirmar", key=f"open_approve_{req['id']}", type="primary"):
                    st.session_state[approve_key] = not st.session_state.get(approve_key, False)
                    st.rerun()

                if st.session_state.get(approve_key):
                    st.markdown("**Revise os dados antes de confirmar:**")
                    with st.form(key=f"approve_form_{req['id']}"):
                        # Boarding / alighting override
                        col_b, col_a = st.columns(2)
                        with col_b:
                            boarding_idx = stops.index(req["boarding_city"]) if req["boarding_city"] in stops else 0
                            boarding_city = st.selectbox("Cidade de embarque", stops, index=boarding_idx)
                        with col_a:
                            alighting_idx = stops.index(req["alighting_city"]) if req["alighting_city"] in stops else len(stops) - 1
                            alighting_city = st.selectbox("Cidade de desembarque", stops, index=alighting_idx)

                        edited_passengers = []
                        for i, p_raw in enumerate(passengers_json):
                            st.markdown(f"---\n**Passageiro {i + 1}**")
                            birth_str = p_raw.get("birth_date", "")
                            minor = is_minor(birth_str)
                            toddler = is_toddler(birth_str)
                            if toddler:
                                st.markdown("🔵 **Menor de 7 anos**")
                            elif minor:
                                st.markdown("🔴 **Menor de idade**")

                            c1, c2 = st.columns(2)
                            with c1:
                                p_name = st.text_input("Nome", value=p_raw.get("name", ""), key=f"pname_{req['id']}_{i}")
                                p_cpf = st.text_input("CPF", value=p_raw.get("cpf", ""), key=f"pcpf_{req['id']}_{i}")
                            with c2:
                                p_rg = st.text_input("RG", value=p_raw.get("rg", ""), key=f"prg_{req['id']}_{i}")
                                try:
                                    birth_val = date.fromisoformat(birth_str) if birth_str else date(1990, 1, 1)
                                except Exception:
                                    birth_val = date(1990, 1, 1)
                                p_birth = st.date_input("Data de nascimento", value=birth_val,
                                    min_value=date(1900, 1, 1), max_value=date.today(),
                                    key=f"pbirth_{req['id']}_{i}")
                            p_phone = st.text_input("Celular", value=p_raw.get("phone", ""),
                                placeholder="(21) 99999-9999", key=f"pphone_{req['id']}_{i}")

                            if toddler:
                                raw_seat_type = p_raw.get("seat_type", "poltrona")
                                seat_type_idx = 1 if raw_seat_type == "colo" else 0
                                p_seat_type = st.selectbox(
                                    "Tipo de assento",
                                    ["poltrona", "colo"],
                                    index=seat_type_idx,
                                    format_func=lambda s: "Poltrona" if s == "poltrona" else "Colo do acompanhante (não ocupa vaga)",
                                    key=f"pseattype_{req['id']}_{i}",
                                )
                            else:
                                p_seat_type = "poltrona"

                            p_notes = st.text_area("Observações (bagagem, etc.)",
                                value=p_raw.get("notes", ""), key=f"pnotes_{req['id']}_{i}", height=60)

                            edited_passengers.append({
                                "name": p_name,
                                "cpf": p_cpf,
                                "rg": p_rg or None,
                                "birth_date": p_birth.isoformat(),
                                "is_minor": is_minor(p_birth.isoformat()),
                                "seat_type": p_seat_type,
                                "phone": p_phone.strip() or None,
                                "notes": p_notes or None,
                            })

                        col_confirm, col_back = st.columns(2)
                        confirm = col_confirm.form_submit_button("✅ Confirmar aprovação", type="primary")
                        cancel = col_back.form_submit_button("⏭️ Avaliar depois")

                    if confirm:
                        errors = [f"Nome do passageiro {i+1} é obrigatório." for i, p in enumerate(edited_passengers) if not p["name"].strip()]
                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            try:
                                leader_name = edited_passengers[0]["name"].strip() if edited_passengers else ""
                                for idx, p in enumerate(edited_passengers):
                                    db.table("passengers").insert({
                                        "trip_id": req["trip_id"],
                                        "boarding_city": boarding_city,
                                        "alighting_city": alighting_city,
                                        "seat_status": "reserved",
                                        "source": "public_request",
                                        "group_leader": None if idx == 0 else leader_name,
                                        **p,
                                    }).execute()
                                db.table("pending_requests").update({
                                    "status": "approved",
                                    "reviewed_at": datetime.utcnow().isoformat(),
                                }).eq("id", req["id"]).execute()
                                st.session_state.pop(approve_key, None)
                                st.success("Solicitação aprovada! Passageiros adicionados à viagem.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao aprovar: {e}")

                    if cancel:
                        st.session_state.pop(approve_key, None)
                        st.rerun()

                # ── Reject ────────────────────────────────────
                reject_key = f"reject_{req['id']}"
                if st.button("❌ Rejeitar", key=f"open_reject_{req['id']}"):
                    st.session_state[reject_key] = not st.session_state.get(reject_key, False)
                    st.rerun()

                if st.session_state.get(reject_key):
                    with st.form(key=f"reject_form_{req['id']}"):
                        rejection_note = st.text_area("Motivo da rejeição (opcional)")
                        confirmed = st.form_submit_button("Confirmar rejeição", type="primary")
                    if confirmed:
                        try:
                            db.table("pending_requests").update({
                                "status": "rejected",
                                "rejection_note": rejection_note.strip() or None,
                                "reviewed_at": datetime.utcnow().isoformat(),
                            }).eq("id", req["id"]).execute()
                            st.session_state.pop(reject_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

                # Raw data
                with st.expander("Ver dados brutos do formulário"):
                    st.json(passengers_json)

# ── Tab: Aprovados ────────────────────────────────────────────
with tab_approved:
    requests = load_requests("approved")
    if not requests:
        st.info("Nenhuma solicitação aprovada ainda.")
    for req in requests:
        trip_info = req.get("trips", {}) or {}
        trip_label = f"{trip_info.get('origin', '?')} → {trip_info.get('destination', '?')} | {fmt_dt(trip_info.get('departure_at'))}"
        st.markdown(f"✅ **{trip_label}** — {req['passenger_count']} passageiro(s) — aprovado em {fmt_dt(req.get('reviewed_at'))}")

# ── Tab: Rejeitados ───────────────────────────────────────────
with tab_rejected:
    requests = load_requests("rejected")
    if not requests:
        st.info("Nenhuma solicitação rejeitada.")
    for req in requests:
        trip_info = req.get("trips", {}) or {}
        trip_label = f"{trip_info.get('origin', '?')} → {trip_info.get('destination', '?')} | {fmt_dt(trip_info.get('departure_at'))}"
        note = f" — *{req['rejection_note']}*" if req.get("rejection_note") else ""
        st.markdown(f"❌ **{trip_label}** — rejeitado em {fmt_dt(req.get('reviewed_at'))}{note}")
