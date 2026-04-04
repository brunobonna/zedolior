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
    return (db.table("pending_requests")
              .select("*, trips(origin, destination, departure_at)")
              .eq("status", status)
              .order("submitted_at", desc=(status == "pending"))
              .execute().data)

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
        for req in requests:
            trip_info = req.get("trips", {}) or {}
            trip_label = f"{trip_info.get('origin', '?')} → {trip_info.get('destination', '?')} | {fmt_dt(trip_info.get('departure_at'))}"
            stops = load_stops(req["trip_id"])
            passengers_json = req.get("passengers_json") or []

            with st.expander(f"📋 {trip_label} — {req['passenger_count']} passageiro(s) — {fmt_dt(req['submitted_at'])}", expanded=True):
                st.markdown(f"**Viagem:** {trip_label}")
                st.markdown(f"**Embarque:** {req['boarding_city']} &nbsp;→&nbsp; **Desembarque:** {req['alighting_city']}")
                st.markdown(f"**Enviado em:** {fmt_dt(req['submitted_at'])}")

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
                            if minor:
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
                            p_notes = st.text_area("Observações (bagagem, etc.)",
                                value=p_raw.get("notes", ""), key=f"pnotes_{req['id']}_{i}", height=60)

                            edited_passengers.append({
                                "name": p_name,
                                "cpf": p_cpf,
                                "rg": p_rg or None,
                                "birth_date": p_birth.isoformat(),
                                "is_minor": is_minor(p_birth.isoformat()),
                                "notes": p_notes or None,
                            })

                        col_confirm, col_back = st.columns(2)
                        confirm = col_confirm.form_submit_button("✅ Confirmar aprovação", type="primary")
                        cancel = col_back.form_submit_button("Cancelar")

                    if confirm:
                        errors = [f"Nome do passageiro {i+1} é obrigatório." for i, p in enumerate(edited_passengers) if not p["name"].strip()]
                        if errors:
                            for e in errors:
                                st.error(e)
                        else:
                            try:
                                for p in edited_passengers:
                                    db.table("passengers").insert({
                                        "trip_id": req["trip_id"],
                                        "boarding_city": boarding_city,
                                        "alighting_city": alighting_city,
                                        "seat_status": "reserved",
                                        "source": "public_request",
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
