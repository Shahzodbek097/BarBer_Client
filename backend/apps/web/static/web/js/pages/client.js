/* `/c/` — mijoz kabineti: navbatlarim (filtr, bekor qilish, qayta rejalash, sharh). */

import {
  api,
  closeModal,
  el,
  fmtDate,
  fmtPrice,
  fmtTime,
  openModal,
  statusTag,
  toast,
} from "../api.js";
import { redirectIfNotRole, wsReload } from "./common.js";

const $ = (id) => document.getElementById(id);

let statusFilter = "";

init();

function init() {
  if (!redirectIfNotRole(["client"])) return;
  $("client-app").classList.remove("hidden");

  document.querySelectorAll("#status-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      statusFilter = tab.dataset.status;
      document.querySelectorAll("#status-tabs .tab").forEach((t) => t.classList.toggle("active", t === tab));
      load();
    });
  });

  document.addEventListener("bb:notify", wsReload(load));
  load();
}

async function load() {
  try {
    const data = await api("bookings/my/", { query: { status: statusFilter } });
    const bookings = data.results || data;
    const highlight = Number(new URLSearchParams(location.search).get("booking")) || 0;

    $("empty").classList.toggle("hidden", bookings.length > 0);
    $("booking-list").innerHTML = "";
    for (const booking of bookings) {
      const card = bookingCard(booking);
      if (highlight && booking.id === highlight) card.classList.add("highlight");
      $("booking-list").appendChild(card);
    }
  } catch (err) {
    toast(err.message, "err");
  }
}

function bookingCard(booking) {
  const actions = [];
  if (booking.status === "pending" || booking.status === "confirmed") {
    actions.push(`<button class="btn btn-sm btn-danger" data-act="cancel">Bekor qilish</button>`);
    actions.push(`<button class="btn btn-sm" data-act="reschedule">Vaqtni o'zgartirish</button>`);
  }
  if (booking.status === "completed") {
    actions.push(`<button class="btn btn-sm btn-primary" data-act="review">Baho berish</button>`);
  }
  const note = booking.client_note ? `<p class="muted">Izoh: ${booking.client_note}</p>` : "";
  const reply = booking.barber_reply ? `<p class="muted">Javob: ${booking.barber_reply}</p>` : "";
  const price = booking.price ? fmtPrice(booking.price) : "";

  const card = el(
    `<div class="card">
       <div class="row-between">
         <h3>${booking.service_name}</h3>
         ${statusTag(booking.status)}
       </div>
       <p class="muted">${fmtDate(booking.date)} · ${fmtTime(booking.start_time)}–${fmtTime(booking.end_time)}</p>
       <p class="muted">${booking.salon_name || "Sartarosh"} · ${booking.client_phone ? "" : ""}</p>
       ${price ? `<p class="money">${price}</p>` : ""}
       ${note}${reply}
       <div class="row mt">${actions.join("")}</div>
     </div>`
  );

  card.querySelector('[data-act="cancel"]')?.addEventListener("click", () => cancelBooking(booking, card));
  card.querySelector('[data-act="reschedule"]')?.addEventListener("click", () => rescheduleModal(booking));
  card.querySelector('[data-act="review"]')?.addEventListener("click", () => reviewModal(booking));
  return card;
}

/* --- Bekor qilish --- */

async function cancelBooking(booking) {
  if (!confirm("Navbatni bekor qilasizmi?")) return;
  try {
    await api(`bookings/${booking.id}/cancel/`, { method: "POST" });
    toast("Navbat bekor qilindi", "ok");
    load();
  } catch (err) {
    toast(err.message, "err");
  }
}

/* --- Qayta rejalash --- */

function rescheduleModal(booking) {
  const overlay = openModal(
    `<h3>Vaqtni o'zgartirish</h3>
     <p class="muted">${booking.service_name} · ${fmtDate(booking.date)} ${fmtTime(booking.start_time)}</p>
     <label for="rs-date">Yangi sana</label>
     <input id="rs-date" type="date">
     <div id="rs-slots" class="slot-grid mt"></div>
     <p id="rs-hint" class="muted mt">Sanani tanlang — bo'sh vaqtlar chiqadi.</p>
     <div class="row mt">
       <button id="rs-save" class="btn btn-primary" disabled>Saqlash</button>
       <button id="rs-close" class="btn">Yopish</button>
     </div>`
  );

  let picked = null;
  const dateInput = overlay.querySelector("#rs-date");
  dateInput.min = new Date().toISOString().slice(0, 10);
  dateInput.addEventListener("change", async () => {
    picked = null;
    overlay.querySelector("#rs-save").disabled = true;
    const box = overlay.querySelector("#rs-slots");
    box.innerHTML = '<span class="muted">Yuklanmoqda...</span>';
    try {
      const slots = await api(`catalog/barbers/${booking.barber_id}/slots/`, {
        query: { service_id: booking.service, day: dateInput.value },
      });
      box.innerHTML = "";
      if (!slots.length) {
        box.innerHTML = '<span class="muted">Bu kunda bo\'sh vaqt yo\'q.</span>';
        return;
      }
      for (const slot of slots) {
        const time = slot.start.includes("T") ? slot.start.slice(11, 16) : slot.start.slice(0, 5);
        const chip = el(`<button class="chip">${time}</button>`);
        chip.addEventListener("click", () => {
          picked = { date: dateInput.value, start_time: time };
          overlay.querySelectorAll("#rs-slots .chip").forEach((c) => c.classList.remove("active"));
          chip.classList.add("active");
          overlay.querySelector("#rs-save").disabled = false;
        });
        box.appendChild(chip);
      }
    } catch (err) {
      box.innerHTML = `<span class="error-text">${err.message}</span>`;
    }
  });

  overlay.querySelector("#rs-close").addEventListener("click", closeModal);
  overlay.querySelector("#rs-save").addEventListener("click", async () => {
    if (!picked) return;
    try {
      await api(`bookings/${booking.id}/reschedule/`, { method: "POST", body: picked });
      toast("Vaqt o'zgartirildi", "ok");
      closeModal();
      load();
    } catch (err) {
      toast(err.message, "err");
    }
  });
}

/* --- Sharh --- */

function reviewModal(booking) {
  const overlay = openModal(
    `<h3>Baho berish</h3>
     <p class="muted">${booking.service_name} · ${fmtDate(booking.date)}</p>
     <div id="rv-stars" class="rating mt" style="font-size:26px; cursor:pointer;">★★★★★</div>
     <label for="rv-comment">Izoh (ixtiyoriy)</label>
     <textarea id="rv-comment" rows="3" maxlength="1000"></textarea>
     <p id="rv-error" class="error-text hidden"></p>
     <div class="row mt">
       <button id="rv-save" class="btn btn-primary">Yuborish</button>
       <button id="rv-close" class="btn">Yopish</button>
     </div>`
  );

  let rating = 5;
  const stars = overlay.querySelector("#rv-stars");
  stars.addEventListener("click", (e) => {
    const rect = stars.getBoundingClientRect();
    rating = Math.max(1, Math.ceil(((e.clientX - rect.left) / rect.width) * 5));
    stars.textContent = "★".repeat(rating) + "☆".repeat(5 - rating);
  });

  overlay.querySelector("#rv-close").addEventListener("click", closeModal);
  overlay.querySelector("#rv-save").addEventListener("click", async () => {
    try {
      await api("reviews/", {
        method: "POST",
        body: {
          appointment: booking.id,
          rating,
          comment: overlay.querySelector("#rv-comment").value.trim(),
        },
      });
      toast("Baho uchun rahmat!", "ok");
      closeModal();
      load();
    } catch (err) {
      const box = overlay.querySelector("#rv-error");
      box.textContent = err.message;
      box.classList.remove("hidden");
    }
  });
}
