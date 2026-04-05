import streamlit as st
from config import get_supabase
from datetime import datetime

def fmt_dt(dt_str):
    if not dt_str:
        return "—"
    try:
        return datetime.fromisoformat(dt_str).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_str

st.title("📊 Painel")

try:
    db = get_supabase()

    active_trips = db.table("trips").select("id, origin, destination, departure_at, total_seats").eq("status", "active").order("departure_at").execute().data
    active_ids   = [t["id"] for t in active_trips]

    # Pendentes SOMENTE de viagens ativas
    all_pending_reqs = db.table("pending_requests").select("id, trip_id").eq("status", "pending").execute().data
    pending_reqs = [r for r in all_pending_reqs if r["trip_id"] in active_ids]

    col1, col2 = st.columns(2)
    col1.metric("Viagens ativas", len(active_trips))
    col2.metric("Solicitações pendentes", len(pending_reqs))

    st.divider()

    if not active_trips:
        st.info("Nenhuma viagem ativa no momento.")
    else:
        all_passengers = (
            db.table("passengers")
            .select("trip_id, seat_status")
            .in_("trip_id", active_ids)
            .execute().data
        ) if active_ids else []

        pending_by_trip = {}
        for r in pending_reqs:
            pending_by_trip[r["trip_id"]] = pending_by_trip.get(r["trip_id"], 0) + 1

        st.subheader("Viagens ativas")

        hc = st.columns([3, 2, 1, 1, 1])
        hc[0].markdown("**Viagem**")
        hc[1].markdown("**Saída**")
        hc[2].markdown("**✅ Pagos**")
        hc[3].markdown("**⏳ Reservados**")
        hc[4].markdown("**🔔 Pendentes**")
        st.divider()

        for trip in active_trips:
            pax      = [p for p in all_passengers if p["trip_id"] == trip["id"]]
            paid     = sum(1 for p in pax if p["seat_status"] == "paid")
            reserved = sum(1 for p in pax if p["seat_status"] == "reserved")
            pend     = pending_by_trip.get(trip["id"], 0)

            rc = st.columns([3, 2, 1, 1, 1])
            rc[0].write(f"**{trip['origin']} → {trip['destination']}**")
            rc[1].write(fmt_dt(trip["departure_at"]))
            rc[2].write(str(paid))
            rc[3].write(str(reserved))
            rc[4].write(f"{'🔴 ' if pend > 0 else ''}{pend}")

except Exception as e:
    st.info("Configure as credenciais do Supabase em `.streamlit/secrets.toml` para conectar ao banco de dados.")
    st.caption(f"Detalhe: {e}")
