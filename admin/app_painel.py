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
            .select("trip_id, seat_status, seat_type")
            .in_("trip_id", active_ids)
            .execute().data
        ) if active_ids else []

        pending_by_trip = {}
        for r in pending_reqs:
            pending_by_trip[r["trip_id"]] = pending_by_trip.get(r["trip_id"], 0) + 1

        st.subheader("Viagens ativas")

        for trip in active_trips:
            pax      = [p for p in all_passengers if p["trip_id"] == trip["id"]]
            occupied = sum(1 for p in pax if p.get("seat_type", "poltrona") != "colo")
            paid     = sum(1 for p in pax if p["seat_status"] == "paid")
            reserved = sum(1 for p in pax if p["seat_status"] == "reserved")
            pend     = pending_by_trip.get(trip["id"], 0)

            with st.container(border=True):
                st.markdown(f"**{trip['origin']} → {trip['destination']}** &nbsp; 🪑 {occupied}/{trip['total_seats']} ocupadas")
                st.caption(f"📅 {fmt_dt(trip['departure_at'])}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🎫 Total vagas", trip["total_seats"])
                c2.metric("✅ Pagos", paid)
                c3.metric("⏳ Reserv.", reserved)
                c4.metric("🔔 Pend.", pend)

except Exception as e:
    st.info("Configure as credenciais do Supabase em `.streamlit/secrets.toml` para conectar ao banco de dados.")
    st.caption(f"Detalhe: {e}")
