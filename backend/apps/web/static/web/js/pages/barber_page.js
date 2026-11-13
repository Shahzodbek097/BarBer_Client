/* `/barber/{id}/` — ochiq sartarosh sahifasi: xizmatlar, bo'sh slotlar, navbat olish.
 * JWT yo'q bo'lsa: navbat intenti sessionStorage'ga saqlanadi → /auth/?next=...
 * Kirgandan keyin sahifa intentni avtomatik tasdiqlaydi.
 */

import { accessToken, api, el, fmtPrice, toast } from "../api.js";

const $ = (id) => document.getElementById(id);
const barberId = Number(location.pathname.split("/")[2]);

const DAY_NAMES = ["Yak", "Dush", "Sesh", "Chor", "Pay", "Jum", "Shan"];
const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyn", "iyl", "avg", "sen", "okt", "noy", "dek"];

let service = null;
let selectedDay = ""; // YYYY-MM-DD
let selectedSlot = null; // {date, start}

init();

async function init() {
  if (!barberId) {
    location.href = "/";
    return;
  }
  await loadBarber();
  await loadReviews();
  const hadIntent = await tryPendingIntent();
  await loadServices();
  if (hadIntent) return; // intent o'zi tanlov qildi
}

/* --- Sartarosh --- */

async function loadBarber() {
  try {
    const barber = await api(`catalog/barbers/${barberId}/`);
    const rating =
      Number(barber.rating_count) > 0
        ? `<span class="rating">★ ${Number(barber.rating_avg).toFixed(1)}</span> <span class="muted">(${barber.rating_count})</span>`
        : "";
    const active = barber.is_active_now
      ? '<span class="tag tag-online">Faol</span>'
      : '<span class="muted">Nofaol</span>';
    $("barber-header").innerHTML = `
      <div class="row-between">
        <h1>${barber.name}</h1>
        ${active}
      </div>
      <p class="muted">${barber.salon_name ? `${barber.salon_name} · ` : ""}${barber.experience_years} yillik tajriba</p>
      ${barber.bio ? `<p class="mt">${barber.bio}</p>` : ""}
      ${barber.specialties && barber.specialties.length ? `<p class="muted mt">${barber.specialties.join(" · ")}</p>` : ""}
      <div class="row mt">${rating}</div>
    `;
    document.title = `${barber.name} — BarBer`;
  } catch (err) {
    $("barber-header").innerHTML = `<p class="empty">Sartarosh topilmadi yoki faol emas.</p>`;
  }
}

/* --- Xizmatlar --- */

async function loadServices() {
  try {
    const services = await api(`catalog/barbers/${barberId}/services/`);
    if (!services.length) {
      $("service-list").innerHTML = '<p class="muted">Xizmatlar hozircha kiritilmagan.</p>';
      return;
    }
    $("service-list").innerHTML = "";
    for (const svc of services) {
      const btn = el(
        `<button class="chip" data-id="${svc.id}">
           ${svc.name} — ${fmtPrice(svc.price)} <span class="muted">(${svc.duration_min} daq)</span>
         </button>`
      );
      btn.addEventListener("click", () => {
        service = svc;
        selectedSlot = null;
        $("service-list").querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        showSlotPanel();
      });
      $("service-list").appendChild(btn);
    }
  } catch (err) {
    $("service-list").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

/* --- Kunlar + slotlar --- */

function dayChips() {
  const chips = [];
  const now = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
    const iso = toISO(d);
    chips.push(
      `<button class="chip ${iso === selectedDay ? "active" : ""}" data-day="${iso}">
         ${i === 0 ? "Bugun" : i === 1 ? "Ertaga" : `${d.getDate()} ${MONTHS[d.getMonth()]}`}
         <span class="muted">, ${DAY_NAMES[d.getDay()]}</span>
       </button>`
    );
  }
  return chips.join("");
}

function toISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function showSlotPanel() {
  $("slot-panel").classList.remove("hidden");
  $("booking-panel").classList.add("hidden");
  $("success-panel").classList.add("hidden");
  const today = new Date();
  selectedDay = selectedDay || toISO(today);
  $("day-chips").innerHTML = dayChips();
  $("day-chips").querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      selectedDay = chip.dataset.day;
      selectedSlot = null;
      $("day-chips").querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      loadSlots();
    });
  });
  loadSlots();
}

function parseSlot(slot) {
  // start: "YYYY-MM-DDTHH:MM:SS" yoki "HH:MM:SS"
  const raw = slot.start;
  if (raw.includes("T")) {
    return { date: raw.slice(0, 10), start: raw.slice(11, 16) };
  }
  return { date: selectedDay, start: raw.slice(0, 5) };
}

async function loadSlots() {
  $("slot-chips").innerHTML = '<span class="muted">Yuklanmoqda...</span>';
  $("slot-empty").classList.add("hidden");
  try {
    const slots = await api(`catalog/barbers/${barberId}/slots/`, {
      query: { service_id: service.id, day: selectedDay },
    });
    if (!slots.length) {
      $("slot-chips").innerHTML = "";
      $("slot-empty").classList.remove("hidden");
      return;
    }
    $("slot-chips").innerHTML = "";
    for (const slot of slots) {
      const { date, start } = parseSlot(slot);
      const chip = el(`<button class="chip">${start}</button>`);
      chip.addEventListener("click", () => {
        selectedSlot = { date, start };
        $("slot-chips").querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        $("booking-panel").classList.remove("hidden");
      });
      $("slot-chips").appendChild(chip);
    }
  } catch (err) {
    $("slot-chips").innerHTML = "";
    $("slot-empty").textContent = err.message;
    $("slot-empty").classList.remove("hidden");
  }
}

/* --- Navbat olish --- */

$("book-btn").addEventListener("click", book);

async function book() {
  if (!selectedSlot) return;
  $("book-btn").disabled = true;
  try {
    const appointment = await api("bookings/", {
      method: "POST",
      body: {
        barber: barberId,
        service: service.id,
        date: selectedSlot.date,
        start_time: selectedSlot.start,
        note: $("f-note").value.trim(),
      },
    });
    sessionStorage.removeItem("bb_pending_booking");
    showSuccess(appointment);
  } catch (err) {
    if (err.status === 401 && !accessToken()) {
      sessionStorage.setItem(
        "bb_pending_booking",
        JSON.stringify({
          barber: barberId,
          service: service.id,
          service_name: service.name,
          date: selectedSlot.date,
          start_time: selectedSlot.start,
          note: $("f-note").value.trim(),
          return_to: location.pathname,
        })
      );
      location.href = `/auth/?next=${encodeURIComponent(location.pathname)}`;
      return;
    }
    toast(err.message, "err");
  } finally {
    $("book-btn").disabled = false;
  }
}

/* Kirgandan qaytgach: saqlangan navbatni avtomatik tasdiqlash */
async function tryPendingIntent() {
  const raw = sessionStorage.getItem("bb_pending_booking");
  if (!raw) return false;
  let intent;
  try {
    intent = JSON.parse(raw);
  } catch {
    sessionStorage.removeItem("bb_pending_booking");
    return false;
  }
  if (!accessToken() || Number(intent.barber) !== barberId) return false; // boshqa sahifada ko'rsatiladi

  sessionStorage.removeItem("bb_pending_booking");
  try {
    const appointment = await api("bookings/", {
      method: "POST",
      body: {
        barber: barberId,
        service: intent.service,
        date: intent.date,
        start_time: intent.start_time,
        note: intent.note || "",
      },
    });
    showSuccess(appointment);
    return true;
  } catch (err) {
    toast(err.message, "err"); // masalan, vaqt allaqachon band
    return false;
  }
}

function showSuccess(appointment) {
  $("slot-panel").classList.add("hidden");
  $("success-panel").classList.remove("hidden");
  $("success-text").textContent = `${appointment.service_name} · ${fmtDate(appointment.date)} ${appointment.start_time.slice(0, 5)} — tasdiqlash kutilmoqda.`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function fmtDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

/* --- Sharhlar --- */

async function loadReviews() {
  try {
    const reviews = await api(`reviews/barber/${barberId}/`);
    if (!reviews.length) {
      $("reviews-empty").classList.remove("hidden");
      return;
    }
    $("review-list").innerHTML = "";
    for (const review of reviews) {
      $("review-list").appendChild(
        el(
          `<div class="list-item">
             <div class="row-between">
               <strong>${review.client_name}</strong>
               <span class="rating">${"★".repeat(review.rating)}${"☆".repeat(5 - review.rating)}</span>
             </div>
             ${review.comment ? `<p class="muted">${review.comment}</p>` : ""}
             ${review.barber_reply ? `<p class="muted">↩ Javob: ${review.barber_reply}</p>` : ""}
           </div>`
        )
      );
    }
  } catch {
    $("reviews-empty").classList.remove("hidden");
  }
}
