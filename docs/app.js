/* ============================================================
   Zé do Lior Viagens — app.js
   ============================================================ */

"use strict";

// ── State ─────────────────────────────────────────────────────
let currentTrip  = null;
let currentStops = [];   // [{city, stop_order}] ordered
let passengerCount = 1;

// ── Supabase REST helper ──────────────────────────────────────
function sbHeaders() {
  return {
    apikey: window.SUPABASE_ANON_KEY,
    Authorization: `Bearer ${window.SUPABASE_ANON_KEY}`,
    "Content-Type": "application/json",
  };
}

async function sbGet(path) {
  const res = await fetch(`${window.SUPABASE_URL}/rest/v1/${path}`, { headers: sbHeaders() });
  if (!res.ok) throw new Error(`Erro ao buscar dados: ${res.status}`);
  return res.json();
}

async function sbPost(path, body) {
  const res = await fetch(`${window.SUPABASE_URL}/rest/v1/${path}`, {
    method: "POST",
    headers: { ...sbHeaders(), Prefer: "return=minimal" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Erro ao enviar: ${res.status} — ${txt}`);
  }
  return true;
}

// ── Date / age helpers ────────────────────────────────────────
function isMinor(birthDateStr) {
  if (!birthDateStr) return false;
  const birth = new Date(birthDateStr + "T00:00:00");
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const m = today.getMonth() - birth.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
  return age < 18;
}

function fmtDate(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtDateShort(isoStr) {
  if (!isoStr) return "—";
  const d = new Date(isoStr);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
}

function fmtPrice(val) {
  return Number(val).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ── Phone mask ────────────────────────────────────────────────
function fmtPhone(input) {
  let v = input.value.replace(/\D/g, "").slice(0, 11);
  if (v.length <= 2)       input.value = v.length ? `(${v}` : "";
  else if (v.length <= 7)  input.value = `(${v.slice(0,2)}) ${v.slice(2)}`;
  else if (v.length <= 11) input.value = `(${v.slice(0,2)}) ${v.slice(2,7)}-${v.slice(7)}`;
}

// ── WhatsApp URL ──────────────────────────────────────────────
function buildWhatsAppUrl(trip, boardingCity, alightingCity, passengers) {
  const tripDate = fmtDateShort(trip.departure_at);
  let msg = `Olá! Quero reservar uma vaga na viagem de *${boardingCity}* para *${alightingCity}* no dia *${tripDate}*.\n\nSeguem meus dados:\n`;

  passengers.forEach((p, i) => {
    const bd = p.birth_date ? new Date(p.birth_date + "T00:00:00").toLocaleDateString("pt-BR") : "—";
    msg += `\n*Passageiro ${i + 1}:* ${p.name}`;
    if (isMinor(p.birth_date)) msg += " _(menor de idade)_";
    msg += `\nCPF: ${p.cpf}`;
    msg += `\nRG: ${p.rg || "não informado"}`;
    msg += `\nNascimento: ${bd}`;
    if (p.phone) msg += `\nCelular: ${p.phone}`;
    msg += `\n`;
  });

  msg += `\nAguardo confirmação. Obrigado!`;
  return `https://wa.me/${window.WHATSAPP_NUMBER}?text=${encodeURIComponent(msg)}`;
}

// ── Trip card renderer ────────────────────────────────────────
function renderTripCard(trip, stops) {
  const available = Number(trip.seats_available);
  const soldOut   = available <= 0;
  const stopCities = stops.map(s => s.city).join(" → ");

  const publicNotesHtml = trip.public_notes
    ? `<div class="trip-public-notes">ℹ️ ${trip.public_notes}</div>`
    : "";

  return `
    <article class="trip-card${soldOut ? " sold-out" : ""}" data-trip-id="${trip.id}">
      <div class="trip-route">${trip.origin} → ${trip.destination}</div>
      <div class="trip-stops">${stopCities}</div>
      <div class="trip-date">📅 ${fmtDate(trip.departure_at)}</div>
      ${publicNotesHtml}
      <div class="trip-meta">
        <div class="trip-seats">
          Vagas: <span class="${soldOut ? "none" : "available"}">${available}</span> / ${trip.total_seats}
        </div>
        <div class="trip-price">${fmtPrice(trip.price)}</div>
      </div>
      <button
        class="btn-reservar"
        data-trip-id="${trip.id}"
        ${soldOut ? "disabled" : ""}
      >${soldOut ? "Esgotado" : "Reservar vaga"}</button>
    </article>
  `;
}

// ── Load and render trips ─────────────────────────────────────
async function loadAndRender() {
  const container = document.getElementById("trips-container");
  const noTrips   = document.getElementById("no-trips");

  // Show skeletons
  container.innerHTML = `<div class="skeleton-card"></div><div class="skeleton-card"></div>`;
  noTrips.classList.add("hidden");

  try {
    const trips = await sbGet("trip_availability?status=eq.active&order=departure_at.asc");
    container.innerHTML = "";

    if (!trips.length) {
      noTrips.classList.remove("hidden");
      return;
    }

    const ids = trips.map(t => t.id).join(",");
    const allStops = await sbGet(`trip_stops?trip_id=in.(${ids})&order=stop_order.asc`);

    const stopsByTrip = {};
    allStops.forEach(s => {
      if (!stopsByTrip[s.trip_id]) stopsByTrip[s.trip_id] = [];
      stopsByTrip[s.trip_id].push(s);
    });

    trips.forEach(trip => {
      const stops = stopsByTrip[trip.id] || [];
      container.insertAdjacentHTML("beforeend", renderTripCard(trip, stops));
    });

    window._tripsData = trips;
    window._stopsData = stopsByTrip;

    container.querySelectorAll(".btn-reservar:not([disabled])").forEach(btn => {
      btn.addEventListener("click", () => openModal(btn.dataset.tripId));
    });

  } catch (err) {
    container.innerHTML = `<p class="error-msg">Erro ao carregar viagens. Tente recarregar a página.</p>`;
    console.error(err);
  }
}

// ── Modal ─────────────────────────────────────────────────────
function openModal(tripId) {
  const trip = (window._tripsData || []).find(t => t.id === tripId);
  if (!trip) return;

  currentTrip  = trip;
  currentStops = (window._stopsData || {})[tripId] || [];
  passengerCount = 1;

  document.getElementById("modal-trip-summary").innerHTML = `
    <strong>${trip.origin} → ${trip.destination}</strong><br>
    📅 ${fmtDate(trip.departure_at)} &nbsp;|&nbsp;
    💰 ${fmtPrice(trip.price)} por pessoa &nbsp;|&nbsp;
    ${trip.seats_available} vaga(s) disponível(is)
    ${trip.public_notes ? `<br><br>ℹ️ <em>${trip.public_notes}</em>` : ""}
  `;

  populateCitySelects();

  const pContainer = document.getElementById("passengers-container");
  pContainer.innerHTML = "";
  pContainer.insertAdjacentHTML("beforeend", passengerBlock(1));

  document.getElementById("reservation-form").classList.remove("hidden");
  document.getElementById("modal-success").classList.add("hidden");
  document.getElementById("form-error").classList.add("hidden");
  document.getElementById("form-error").textContent = "";

  document.getElementById("modal-overlay").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  document.body.style.overflow = "";
  currentTrip = null;
}

function populateCitySelects() {
  // Embarque: todas as cidades EXCETO a última (destino final)
  const boardingStops  = currentStops.slice(0, -1);
  // Desembarque: todas as cidades EXCETO a primeira (origem)
  const alightingStops = currentStops.slice(1);

  const boardingSel  = document.getElementById("boarding-city");
  const alightingSel = document.getElementById("alighting-city");

  boardingSel.innerHTML = boardingStops.map(
    (s, i) => `<option value="${s.city}" ${i === 0 ? "selected" : ""}>${s.city}</option>`
  ).join("");

  alightingSel.innerHTML = alightingStops.map(
    (s, i) => `<option value="${s.city}" ${i === alightingStops.length - 1 ? "selected" : ""}>${s.city}</option>`
  ).join("");
}

// ── Passenger block HTML ──────────────────────────────────────
function passengerBlock(num) {
  const removable = num > 1;
  return `
    <div class="passenger-block" id="passenger-${num}">
      <div class="passenger-title">
        Passageiro ${num}
        <span class="minor-badge hidden" id="minor-badge-${num}">Menor de idade</span>
      </div>
      ${removable ? `<button type="button" class="remove-passenger" onclick="removePassenger(${num})" aria-label="Remover passageiro ${num}">✕</button>` : ""}
      <div class="form-group">
        <label for="p${num}-name">Nome completo *</label>
        <input type="text" id="p${num}-name" name="p${num}-name" autocomplete="name" placeholder="Nome como no documento" required />
      </div>
      <div class="form-group">
        <label for="p${num}-cpf">CPF *</label>
        <input type="text" id="p${num}-cpf" name="p${num}-cpf" placeholder="000.000.000-00" required />
      </div>
      <div class="form-group">
        <label for="p${num}-rg">RG (identidade)</label>
        <input type="text" id="p${num}-rg" name="p${num}-rg" placeholder="Opcional" />
      </div>
      <div class="form-group">
        <label for="p${num}-birth">Data de nascimento *</label>
        <input type="date" id="p${num}-birth" name="p${num}-birth"
          max="${new Date().toISOString().split("T")[0]}"
          oninput="checkMinor(${num})" required />
      </div>
      <div class="form-group">
        <label for="p${num}-phone">Celular <span class="field-hint">(xx) xxxxx-xxxx</span></label>
        <input type="tel" id="p${num}-phone" name="p${num}-phone"
          placeholder="(21) 99999-9999" maxlength="15"
          oninput="fmtPhone(this)" />
      </div>
    </div>
  `;
}

function checkMinor(num) {
  const birthInput = document.getElementById(`p${num}-birth`);
  const badge      = document.getElementById(`minor-badge-${num}`);
  if (!birthInput || !badge) return;
  badge.classList.toggle("hidden", !isMinor(birthInput.value));
}

function removePassenger(num) {
  const block = document.getElementById(`passenger-${num}`);
  if (block) block.remove();
  passengerCount--;
}

// ── Collect form data ─────────────────────────────────────────
function collectPassengers() {
  const passengers = [];
  const blocks = document.querySelectorAll(".passenger-block");
  for (const block of blocks) {
    const num   = block.id.replace("passenger-", "");
    const name  = (document.getElementById(`p${num}-name`)?.value  || "").trim();
    const cpf   = (document.getElementById(`p${num}-cpf`)?.value   || "").trim();
    const rg    = (document.getElementById(`p${num}-rg`)?.value    || "").trim();
    const birth = document.getElementById(`p${num}-birth`)?.value  || "";
    const phone = (document.getElementById(`p${num}-phone`)?.value || "").trim();
    passengers.push({ name, cpf, rg: rg || null, birth_date: birth, phone: phone || null });
  }
  return passengers;
}

function validateForm(passengers, boardingCity, alightingCity) {
  const errors = [];
  if (!boardingCity)  errors.push("Selecione a cidade de embarque.");
  if (!alightingCity) errors.push("Selecione a cidade de desembarque.");
  if (boardingCity && alightingCity && boardingCity === alightingCity) {
    errors.push("Embarque e desembarque não podem ser na mesma cidade.");
  }
  passengers.forEach((p, i) => {
    if (!p.name)       errors.push(`Nome do passageiro ${i + 1} é obrigatório.`);
    if (!p.cpf)        errors.push(`CPF do passageiro ${i + 1} é obrigatório.`);
    if (!p.birth_date) errors.push(`Data de nascimento do passageiro ${i + 1} é obrigatória.`);
  });
  return errors;
}

// ── DOMContentLoaded ──────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Footer WhatsApp link
  const footerLink = document.getElementById("footer-whatsapp");
  if (footerLink) footerLink.href = `https://wa.me/${window.WHATSAPP_NUMBER}`;

  // Botão recarregar
  const reloadBtn = document.getElementById("reload-btn");
  if (reloadBtn) reloadBtn.addEventListener("click", loadAndRender);

  // Load trips
  loadAndRender();

  // Modal close
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", e => {
    if (e.target === document.getElementById("modal-overlay")) closeModal();
  });
  document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

  // Add passenger
  document.getElementById("add-passenger-btn").addEventListener("click", () => {
    passengerCount++;
    document.getElementById("passengers-container")
      .insertAdjacentHTML("beforeend", passengerBlock(passengerCount));
  });

  // Close success
  document.getElementById("close-success-btn").addEventListener("click", closeModal);

  // Form submit
  document.getElementById("reservation-form").addEventListener("submit", async e => {
    e.preventDefault();

    const boardingCity  = document.getElementById("boarding-city").value;
    const alightingCity = document.getElementById("alighting-city").value;
    const passengers    = collectPassengers();
    const errors        = validateForm(passengers, boardingCity, alightingCity);

    const errorBox = document.getElementById("form-error");
    if (errors.length) {
      errorBox.textContent = errors.join(" • ");
      errorBox.classList.remove("hidden");
      errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    errorBox.classList.add("hidden");

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Abrindo WhatsApp...";

    // ⚠️ Abre o WhatsApp ANTES de qualquer await, ainda no contexto
    // do gesto do usuário — necessário para não ser bloqueado no mobile.
    const waUrl = buildWhatsAppUrl(currentTrip, boardingCity, alightingCity, passengers);
    window.location.href = waUrl;

    // Envia para o Supabase em segundo plano (não bloqueia a abertura do WA)
    sbPost("pending_requests", {
      trip_id: currentTrip.id,
      boarding_city: boardingCity,
      alighting_city: alightingCity,
      passenger_count: passengers.length,
      passengers_json: passengers,
    }).catch(err => console.error("Erro ao registrar solicitação:", err));

    document.getElementById("reservation-form").classList.add("hidden");
    document.getElementById("modal-success").classList.remove("hidden");
    submitBtn.disabled = false;
    submitBtn.textContent = "📱 Confirmar e abrir WhatsApp";
  }); // form submit
}); // DOMContentLoaded
