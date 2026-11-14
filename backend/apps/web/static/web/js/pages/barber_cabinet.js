/* `/barber/` — sartarosh kabineti: status, kelayotgan navbatlar, qo'lda yozish.
 * Profil yo'q bo'lsa (404) — onboarding formasi ko'rinadi.
 */

import {
  api,
  closeModal,
  downloadFile,
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

let profile = null;
let statusFilter = "";
let dayFilter = ""; // "Bugun" chipi: YYYY-MM-DD

init();

function init() {
  if (!redirectIfNotRole(["barber"])) return;

  $("ob-save").addEventListener("click", createProfile);
  $("status-switch").addEventListener("change", toggleStatus);
  $("reload-btn").addEventListener("click", loadIncoming);
  $("m-save").addEventListener("click", manualBooking);
  $("export-btn").addEventListener("click", exportToday);
  $("today-chip").addEventListener("click", () => {
    dayFilter = dayFilter ? "" : new Date().toISOString().slice(0, 10);
    $("today-chip").classList.toggle("active", Boolean(dayFilter));
    loadIncoming();
  });
  $("incoming-tabs").querySelectorAll("[data-status]").forEach((chip) => {
    chip.addEventListener("click", () => {
      statusFilter = chip.dataset.status;
      $("incoming-tabs").querySelectorAll("[data-status]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      loadIncoming();
    });
  });

  document.addEventListener("bb:notify", wsReload(loadIncoming));
  boot();
}

async function boot() {
  try {
    profile = await api("barber/profile/");
    enterCabinet();
  } catch (err) {
    if (err.status === 404) {
      $("onboarding").classList.remove("hidden");
      $("guard").innerHTML = "";
    } else {
      $("guard").innerHTML = `<p class="empty">Xatolik: ${err.message}</p>`;
    }
  }
}

/* --- Onboarding --- */

async function exportToday() {
  $("export-error").classList.add("hidden");
  const day = new Date().toISOString().slice(0, 10);
  try {
    await downloadFile("barber/report/", { day, format: "xlsx" }, `barber-report-${day}.xlsx`);
    toast("Hisobot yuklab olindi", "ok");
  } catch (err) {
    const box = $("export-error");
    box.textContent = err.message;
    box.classList.remove("hidden");
  }
}

async function createProfile() {
  $("ob-error").classList.add("hidden");
  try {
    profile = await api("barber/profile/", {
      method: "POST",
      body: {
        bio: $("ob-bio").value.trim(),
        experience_years: Number($("ob-exp").value || 0),
      },
    });
    toast("Profil yaratildi!", "ok");
    enterCabinet();
  } catch (err) {
    $("barber-app").classList.remove("hidden");
    const box = $("ob-error");
    box.textContent = err.message;
    box.classList.remove("hidden");
  }
}

async function enterCabinet() {
  $("barber-app").classList.remove("hidden");
  $("onboarding").classList.add("hidden");
  $("cabinet").classList.remove("hidden");
  $("guard").innerHTML = "";
  $("status-switch").checked = Boolean(profile.is_active_now);
  $("status-label").textContent = profile.is_active_now ? "Faol" : "Nofaol";
  await loadManualServices();
  loadIncoming();
}

/* --- Faol/Nofaol --- */

async function toggleStatus() {
  const is_active = $("status-switch").checked;
  try {
    const data = await api("barber/status/", { method: "POST", body: { is_active } });
    $("status-label").textContent = data.is_active_now ? "Faol" : "Nofaol";
    toast(data.is_active_now ? "Faol rejimda — mijozlar navbat olishi mumkin" : "Nofaol rejimga o'tdingiz", "ok");
  } catch (err) {
    $("status-switch").checked = !is_active;
    toast(err.message, "err");
  }
}

/* --- Kelayotgan navbatlar --- */

async function loadIncoming() {
  $("incoming-list").innerHTML = '<p class="loading">Yuklanmoqda...</p>';
  try {
    const data = await api("bookings/incoming/", { query: { status: statusFilter, day: dayFilter } });
    const bookings = data.results || data;
    $("incoming-count").textContent = `(${bookings.length})`;
    $("incoming-empty").classList.toggle("hidden", bookings.length > 0);
    $("incoming-list").innerHTML = "";
    for (const booking of bookings) {
      $("incoming-list").appendChild(incomingCard(booking));
    }
  } catch (err) {
    $("incoming-list").innerHTML = "";
    toast(err.message, "err");
  }
}

function incomingCard(booking) {
  const acts = [];
  if (booking.status === "pending") {
    acts.push('<button class="btn btn-sm btn-primary" data-act="confirm">Tasdiqlash</button>');
    acts.push('<button class="btn btn-sm" data-act="propose">Boshqa vaqt</button>');
    acts.push('<button class="btn btn-sm btn-danger" data-act="reject">Rad etish</button>');
  } else if (booking.status === "confirmed") {
    acts.push('<button class="btn btn-sm btn-primary" data-act="complete">Bajarildi</button>');
    acts.push('<button class="btn btn-sm" data-act="no-show">Kelmadi</button>');
    acts.push('<button class="btn btn-sm btn-danger" data-act="cancel">Bekor qilish</button>');
  }
  const source =
    booking.source === "manual" || booking.source === "walk_in"
      ? '<span class="muted">· Qo\'lda</span>'
      : "";
  const note = booking.client_note ? `<p class="muted">Izoh: ${booking.client_note}</p>` : "";
  const reply = booking.barber_reply ? `<p class="muted">Javob: ${booking.barber_reply}</p>` : "";

  const card = el(
    `<div class="list-item">
       <div class="row-between">
         <strong>${booking.client_name}</strong>
         ${statusTag(booking.status)}
       </div>
       <p class="muted">${fmtDate(booking.date)} · ${fmtTime(booking.start_time)}–${fmtTime(booking.end_time)} · ${booking.service_name} ${price(booking)}${source}</p>
       ${note}${reply}
       <div class="row mt">${acts.join("")}</div>
     </div>`
  );

  const act = (name, fn) => card.querySelector(`[data-act="${name}"]`)?.addEventListener("click", fn);
  act("confirm", () => simpleAction(booking.id, "confirm", "Tasdiqlandi"));
  act("complete", () => simpleAction(booking.id, "complete", "Bajarildi deb belgilandi"));
  act("no-show", () => simpleAction(booking.id, "no-show", "Kelmadi deb belgilandi"));
  act("cancel", () => simpleAction(booking.id, "cancel", "Bekor qilindi"));
  act("reject", () => rejectModal(booking.id));
  act("propose", () => proposeModal(booking));
  return card;
}

function price(booking) {
  return booking.price ? ` · ${fmtPrice(booking.price)}` : "";
}

async function simpleAction(id, action, okText) {
  try {
    await api(`bookings/${id}/${action}/`, { method: "POST" });
    toast(okText, "ok");
    loadIncoming();
  } catch (err) {
    toast(err.message, "err");
  }
}

function rejectModal(id) {
  const overlay = openModal(
    `<h3>Rad etish</h3>
     <p class="muted">Sabab yozsangiz, mijoz xabarnomada ko'radi.</p>
     <label for="rj-reply">Javob</label>
     <textarea id="rj-reply" rows="3" maxlength="500" placeholder="Masalan: shu kunda ta'tildaman"></textarea>
     <div class="row mt">
       <button id="rj-send" class="btn btn-danger">Rad etish</button>
       <button id="rj-close" class="btn">Yopish</button>
     </div>`
  );
  overlay.querySelector("#rj-close").addEventListener("click", closeModal);
  overlay.querySelector("#rj-send").addEventListener("click", async () => {
    try {
      await api(`bookings/${id}/reject/`, {
        method: "POST",
        body: { reply: overlay.querySelector("#rj-reply").value.trim() },
      });
      toast("Rad etildi", "ok");
      closeModal();
      loadIncoming();
    } catch (err) {
      toast(err.message, "err");
    }
  });
}

/* --- Boshqa vaqt taklifi --- */

function proposeModal(booking) {
  const overlay = openModal(
    `<h3>Boshqa vaqt taklif qilish</h3>
     <p class="muted">${booking.service_name} · ${fmtDate(booking.date)} ${fmtTime(booking.start_time)}</p>
     <label for="pr-date">Sana</label>
     <input id="pr-date" type="date">
     <div id="pr-slots" class="slot-grid mt"></div>
     <p id="pr-hint" class="muted mt">Sanani tanlang — bo'sh vaqtlar chiqadi.</p>
     <div class="row mt">
       <button id="pr-send" class="btn btn-primary" disabled>Taklif yuborish</button>
       <button id="pr-close" class="btn">Yopish</button>
     </div>`
  );

  let picked = null;
  const dateInput = overlay.querySelector("#pr-date");
  dateInput.min = new Date().toISOString().slice(0, 10);
  dateInput.addEventListener("change", async () => {
    picked = null;
    overlay.querySelector("#pr-send").disabled = true;
    const box = overlay.querySelector("#pr-slots");
    box.innerHTML = '<span class="muted">Yuklanmoqda...</span>';
    try {
      const slots = await api(`catalog/barbers/${profile.id}/slots/`, {
        query: { service_id: booking.service, day: dateInput.value },
      });
      box.innerHTML = "";
      if (!slots.length) {
        box.innerHTML = "<span class='muted'>Bu kunda bo'sh vaqt yo'q.</span>";
        return;
      }
      for (const slot of slots) {
        const time = slot.start.includes("T") ? slot.start.slice(11, 16) : slot.start.slice(0, 5);
        const chip = el(`<button class="chip">${time}</button>`);
        chip.addEventListener("click", () => {
          picked = { date: dateInput.value, start_time: time };
          overlay.querySelectorAll("#pr-slots .chip").forEach((c) => c.classList.remove("active"));
          chip.classList.add("active");
          overlay.querySelector("#pr-send").disabled = false;
        });
        box.appendChild(chip);
      }
    } catch (err) {
      box.innerHTML = `<span class="error-text">${err.message}</span>`;
    }
  });

  overlay.querySelector("#pr-close").addEventListener("click", closeModal);
  overlay.querySelector("#pr-send").addEventListener("click", async () => {
    if (!picked) return;
    try {
      await api(`bookings/${booking.id}/propose/`, { method: "POST", body: picked });
      toast("Taklif yuborildi", "ok");
      closeModal();
      loadIncoming();
    } catch (err) {
      toast(err.message, "err");
    }
  });
}

/* --- Qo'lda navbat yozish --- */

async function loadManualServices() {
  try {
    const services = await api(`catalog/barbers/${profile.id}/services/`);
    $("m-service").innerHTML = services.length
      ? services.map((s) => `<option value="${s.id}">${s.name} (${s.duration_min} daq)</option>`).join("")
      : '<option value="">Xizmat qo\'shilmagan — Profil va jadval sahifasida qo\'shing</option>';
  } catch (err) {
    $("m-service").innerHTML = `<option value="">${err.message}</option>`;
  }
  $("m-date").value = new Date().toISOString().slice(0, 10);
}

async function manualBooking() {
  $("m-error").classList.add("hidden");
  try {
    await api("bookings/manual/", {
      method: "POST",
      body: {
        client_phone: $("m-phone").value.trim().replace(/[\s()-]/g, ""),
        service: Number($("m-service").value),
        date: $("m-date").value,
        start_time: $("m-time").value,
        note: "",
      },
    });
    toast("Navbat yozildi!", "ok");
    $("m-phone").value = "";
    $("m-time").value = "";
    loadIncoming();
  } catch (err) {
    const box = $("m-error");
    box.textContent = err.message;
    box.classList.remove("hidden");
  }
}
