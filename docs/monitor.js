/* ============================================================
   Zé do Lior Viagens — monitor.js
   ============================================================ */

"use strict";

// ── Supabase helpers ──────────────────────────────────────────
function sbHeaders() {
  return {
    apikey: window.SUPABASE_ANON_KEY,
    Authorization: `Bearer ${window.SUPABASE_ANON_KEY}`,
    "Content-Type": "application/json",
  };
}

async function sbGet(path) {
  const res = await fetch(`${window.SUPABASE_URL}/rest/v1/${path}`, { headers: sbHeaders() });
  if (!res.ok) throw new Error(`Erro: ${res.status}`);
  return res.json();
}

async function sbRpc(fn, params = {}) {
  const res = await fetch(`${window.SUPABASE_URL}/rest/v1/rpc/${fn}`, {
    method: "POST",
    headers: sbHeaders(),
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Erro RPC ${fn}: ${res.status}`);
  return res.json();
}

// ── Helpers ───────────────────────────────────────────────────
function fmtDate(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function whatsappUrl(phone) {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  const number = digits.startsWith("55") ? digits : `55${digits}`;
  return `https://wa.me/${number}`;
}

// ── Auth ──────────────────────────────────────────────────────
function isLoggedIn() {
  return sessionStorage.getItem("monitor_auth") === "1";
}

function login(password) {
  if (password.toLowerCase().trim() === window.MONITOR_PASSWORD.toLowerCase()) {
    sessionStorage.setItem("monitor_auth", "1");
    return true;
  }
  return false;
}

function logout() {
  sessionStorage.removeItem("monitor_auth");
  location.reload();
}

// ── Dashboard ─────────────────────────────────────────────────
async function loadDashboard() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("dashboard").classList.remove("hidden");

  const tripsContainer = document.getElementById("monitor-trips");
  tripsContainer.innerHTML = `<p class="mon-loading">Carregando viagens...</p>`;

  try {
    const [trips, passengers, pendingCounts] = await Promise.all([
      sbGet("trip_availability?status=eq.active&order=departure_at.asc"),
      sbRpc("get_passengers_for_monitor"),
      sbRpc("get_trip_pending_counts"),
    ]);

    if (!trips.length) {
      tripsContainer.innerHTML = `<p class="mon-empty">Nenhuma viagem ativa no momento.</p>`;
      return;
    }

    const tripIds = trips.map(t => t.id).join(",");
    const allStops = await sbGet(`trip_stops?trip_id=in.(${tripIds})&order=stop_order.asc`);
    const stopsByTrip = {};
    allStops.forEach(s => {
      if (!stopsByTrip[s.trip_id]) stopsByTrip[s.trip_id] = [];
      stopsByTrip[s.trip_id].push(s.city);
    });

    const pendingMap = {};
    (pendingCounts || []).forEach(r => {
      pendingMap[r.trip_id] = Number(r.pending_passengers || 0);
    });

    tripsContainer.innerHTML = "";
    trips.forEach(trip => {
      const tripPax  = (passengers || []).filter(p => p.trip_id === trip.id);
      const paid     = tripPax.filter(p => p.seat_status === "paid");
      const reserved = tripPax.filter(p => p.seat_status === "reserved");
      const pending  = pendingMap[trip.id] || 0;
      const stops    = stopsByTrip[trip.id] || [];
      tripsContainer.insertAdjacentHTML("beforeend", renderTripCard(trip, stops, paid, reserved, pending));
    });

    attachHandlers(tripsContainer);

  } catch (err) {
    tripsContainer.innerHTML = `<p class="mon-error">Erro ao carregar dados. Tente atualizar.</p>`;
    console.error(err);
  }
}

// ── Render ────────────────────────────────────────────────────
function renderTripCard(trip, stops, paid, reserved, pendingCount) {
  const tid = trip.id;
  const fullRoute = stops.length > 0 ? stops.join(" → ") : `${trip.origin} → ${trip.destination}`;

  const paidBadge = paid.length
    ? `<button class="mon-badge badge-paid" data-expandable data-target="paid-${tid}">✅ ${paid.length} Pago${paid.length !== 1 ? "s" : ""}</button>`
    : `<span class="mon-badge badge-empty">✅ 0 Pagos</span>`;

  const resBadge = reserved.length
    ? `<button class="mon-badge badge-reserved" data-expandable data-target="reserved-${tid}">⏳ ${reserved.length} Reservado${reserved.length !== 1 ? "s" : ""}</button>`
    : `<span class="mon-badge badge-empty">⏳ 0 Reservados</span>`;

  const pendBadge = pendingCount
    ? `<button class="mon-badge badge-pending" data-expandable data-target="pending-${tid}">🔔 ${pendingCount} Pendente${pendingCount !== 1 ? "s" : ""}</button>`
    : `<span class="mon-badge badge-empty">🔔 0 Pendentes</span>`;

  const paidList     = paid.map(p => paxItem(p)).join("") || `<p class="mon-empty-list">Nenhum passageiro pago.</p>`;
  const reservedList = reserved.map(p => paxItem(p)).join("") || `<p class="mon-empty-list">Nenhum passageiro reservado.</p>`;
  const pendingMsg   = `<p class="mon-pending-info">Há ${pendingCount} pessoa(s) aguardando confirmação.<br>Acesse o painel admin para ver e aprovar.</p>`;

  const seatsHtml = `<div class="mon-trip-seats">🚌 ${trip.total_seats} vagas — ${trip.seats_taken} ocupada${trip.seats_taken !== 1 ? "s" : ""}, ${trip.seats_available} disponível${trip.seats_available !== 1 ? "is" : ""}</div>`;
  const notesHtml = trip.notes
    ? `<div class="mon-trip-notes mon-notes-internal">🔒 ${trip.notes}</div>` : "";
  const pubNotesHtml = trip.public_notes
    ? `<div class="mon-trip-notes mon-notes-public">ℹ️ ${trip.public_notes}</div>` : "";

  return `
    <div class="mon-trip-card">
      <div class="mon-trip-route">${trip.origin} → ${trip.destination}</div>
      <div class="mon-trip-stops">${fullRoute}</div>
      <div class="mon-trip-date">📅 ${fmtDate(trip.departure_at)}</div>
      ${seatsHtml}${notesHtml}${pubNotesHtml}
      <div class="mon-badges">${paidBadge} ${resBadge} ${pendBadge}</div>
      <div class="mon-pax-list hidden" id="paid-${tid}">${paidList}</div>
      <div class="mon-pax-list hidden" id="reserved-${tid}">${reservedList}</div>
      <div class="mon-pax-list hidden" id="pending-${tid}">${pendingMsg}</div>
    </div>
  `;
}

function paxItem(p) {
  const data = encodeURIComponent(JSON.stringify(p));
  const group = p.group_leader ? ` <span class="mon-group">(${p.group_leader})</span>` : "";
  const colo = p.seat_type === "colo" ? ` <span class="mon-group">colo</span>` : "";
  return `<button class="mon-pax-name" data-pax="${data}">${p.name}${group}${colo}</button>`;
}

function attachHandlers(container) {
  container.querySelectorAll(".mon-badge[data-expandable]").forEach(badge => {
    badge.addEventListener("click", () => toggleList(badge));
  });
  container.querySelectorAll(".mon-pax-name").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = JSON.parse(decodeURIComponent(btn.dataset.pax));
      showPaxModal(p);
    });
  });
}

function toggleList(badge) {
  const targetId = badge.dataset.target;
  const list     = document.getElementById(targetId);
  if (!list) return;

  const card = badge.closest(".mon-trip-card");
  const wasOpen = !list.classList.contains("hidden");

  card.querySelectorAll(".mon-pax-list").forEach(l => l.classList.add("hidden"));
  card.querySelectorAll(".mon-badge[data-expandable]").forEach(b => b.classList.remove("active"));

  if (!wasOpen) {
    list.classList.remove("hidden");
    badge.classList.add("active");
  }
}

// ── Passenger modal ───────────────────────────────────────────
function showPaxModal(p) {
  const modal   = document.getElementById("pax-modal");
  const content = document.getElementById("pax-modal-content");

  const statusLabel = p.seat_status === "paid" ? "✅ Pago" : "⏳ Reservado";
  const coloLabel   = p.seat_type === "colo" ? " — Colo" : "";

  const waUrl     = p.phone ? whatsappUrl(p.phone) : null;
  const phoneHtml = waUrl
    ? `<a class="mon-phone-link" href="${waUrl}" target="_blank">💬 WhatsApp — ${p.phone}</a>`
    : `<span class="mon-no-phone">Telefone não informado</span>`;

  content.innerHTML = `
    <h3>${p.name}</h3>
    <p class="mon-detail-status">${statusLabel}${coloLabel}</p>
    ${p.boarding_city ? `<p>🚌 Embarque: <strong>${p.boarding_city}</strong></p>` : ""}
    ${p.alighting_city ? `<p>🏁 Desembarque: <strong>${p.alighting_city}</strong></p>` : ""}
    ${p.group_leader ? `<p class="mon-group-info">Grupo: ${p.group_leader}</p>` : ""}
    <div class="mon-phone-section">${phoneHtml}</div>
  `;

  modal.classList.remove("hidden");
}

// ── DOMContentLoaded ──────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  if (isLoggedIn()) {
    loadDashboard();
  }

  document.getElementById("login-form").addEventListener("submit", e => {
    e.preventDefault();
    const pw = document.getElementById("login-password").value;
    if (login(pw)) {
      document.getElementById("login-error").classList.add("hidden");
      loadDashboard();
    } else {
      document.getElementById("login-error").classList.remove("hidden");
      document.getElementById("login-password").value = "";
      document.getElementById("login-password").focus();
    }
  });

  document.getElementById("logout-btn").addEventListener("click", logout);
  document.getElementById("refresh-btn").addEventListener("click", loadDashboard);

  document.getElementById("pax-modal-close").addEventListener("click", () => {
    document.getElementById("pax-modal").classList.add("hidden");
  });
  document.getElementById("pax-modal").addEventListener("click", e => {
    if (e.target.id === "pax-modal") {
      document.getElementById("pax-modal").classList.add("hidden");
    }
  });
});
