/* `/barber/profile/` — profil, xizmatlar, haftalik jadval, tanaffuslar, dam olish kunlari. */

import { api, closeModal, el, fmtPrice, openModal, toast } from "../api.js";
import { redirectIfNotRole } from "./common.js";

const $ = (id) => document.getElementById(id);

const DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"];
const DAYS_TIL = ["Dushanbaga", "Seshanbaga", "Chorshanbaga", "Payshanbaga", "Jumaga", "Shanbaga", "Yakshanbaga"];

let profile = null;
let categories = []; // {id, name}
let schedule = []; // 7 qator

init();

function init() {
  if (!redirectIfNotRole(["barber"])) return;

  $("p-save").addEventListener("click", saveProfile);
  $("s-add-open").addEventListener("click", () => serviceModal(null));
  $("sch-save").addEventListener("click", saveSchedule);
  $("b-add").addEventListener("click", addBreak);
  $("d-add").addEventListener("click", addDayOff);

  loadAll();
}

async function loadAll() {
  // Kategoriya va profil poygasi yo'q — ikkala javob kelinadi, keyin chizamiz
  const [cats, prof] = await Promise.allSettled([
    api("catalog/categories/"),
    api("barber/profile/"),
  ]);
  categories = cats.status === "fulfilled" ? cats.value : [];

  if (prof.status === "rejected") {
    $("guard").innerHTML =
      `<p class="empty">Profil topilmadi — avval <a href="/barber/">kabinetda</a> profil yarating.</p>`;
    return;
  }
  profile = prof.value;
  $("guard").innerHTML = "";
  $("profile-app").classList.remove("hidden");
  $("p-bio").value = profile.bio || "";
  $("p-exp").value = profile.experience_years || 0;

  // profil mutaxassisliklari nomlari bilan keladi → kategoriya id'lariga o'tkazamiz
  const names = profile.specialties || [];
  savedSpecialtyIds = names
    .map((name) => categories.find((c) => c.name === name)?.id)
    .filter(Boolean);
  renderSpecialties();

  await Promise.all([loadServices(), loadSchedule(), loadBreaks(), loadDayOffs()]);
}

function renderSpecialties() {
  $("p-specialties").innerHTML = categories
    .map(
      (c) =>
        `<button type="button" class="chip ${savedSpecialtyIds.includes(c.id) ? "active" : ""}" data-id="${c.id}">${c.name}</button>`
    )
    .join("");
  $("p-specialties").querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => chip.classList.toggle("active"));
  });
}

let savedSpecialtyIds = [];

async function saveProfile() {
  const ids = [...$("p-specialties").querySelectorAll(".chip.active")].map((c) => Number(c.dataset.id));
  try {
    profile = await api("barber/profile/", {
      method: "PATCH",
      body: {
        bio: $("p-bio").value.trim(),
        experience_years: Number($("p-exp").value || 0),
        specialties: ids,
      },
    });
    savedSpecialtyIds = ids;
    toast("Profil saqlandi", "ok");
  } catch (err) {
    toast(err.message, "err");
  }
}

/* --- Xizmatlar --- */

async function loadServices() {
  try {
    const services = await api("barber/services/");
    $("s-empty").classList.toggle("hidden", services.length > 0);
    $("s-list").innerHTML = "";
    for (const svc of services) {
      const state = svc.is_active
        ? ""
        : '<span class="tag tag-cancelled">O\'chirilgan</span>';
      const card = el(
        `<div class="list-item">
           <div class="row-between">
             <strong>${svc.name}</strong>
             <span class="money">${fmtPrice(svc.price)}</span>
           </div>
           <p class="muted">${svc.category_name || ""} · ${svc.duration_min} daq ${state}</p>
           ${svc.description ? `<p class="muted">${svc.description}</p>` : ""}
           <div class="row mt">
             <button class="btn btn-sm" data-act="edit">Tahrirlash</button>
             ${svc.is_active ? '<button class="btn btn-sm btn-danger" data-act="delete">O\'chirish</button>' : ""}
           </div>
         </div>`
      );
      card.querySelector('[data-act="edit"]').addEventListener("click", () => serviceModal(svc));
      card.querySelector('[data-act="delete"]')?.addEventListener("click", async () => {
        try {
          await api(`barber/services/${svc.id}/`, { method: "DELETE" });
          toast("Xizmat o'chirildi", "ok");
          loadServices();
        } catch (err) {
          toast(err.message, "err");
        }
      });
      $("s-list").appendChild(card);
    }
  } catch (err) {
    $("s-list").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

function serviceModal(existing) {
  const isEdit = Boolean(existing);
  const overlay = openModal(
    `<h3>${isEdit ? "Xizmatni tahrirlash" : "Yangi xizmat"}</h3>
     <label for="sv-name">Nomi</label>
     <input id="sv-name" maxlength="200" value="${existing ? existing.name : ""}">
     <div class="form-row">
       <div>
         <label for="sv-cat">Kategoriya</label>
         <select id="sv-cat">
           ${categories.map((c) => `<option value="${c.id}" ${existing && existing.category === c.id ? "selected" : ""}>${c.name}</option>`).join("")}
         </select>
       </div>
       <div>
         <label for="sv-dur">Davomiyligi (daqiqa)</label>
         <input id="sv-dur" type="number" min="5" max="480" value="${existing ? existing.duration_min : 30}">
       </div>
     </div>
     <label for="sv-price">Narxi (so'm)</label>
     <input id="sv-price" type="number" min="0" value="${existing ? existing.price : ""}">
     <label for="sv-desc">Tavsif (ixtiyoriy)</label>
     <textarea id="sv-desc" rows="2" maxlength="500">${existing ? existing.description || "" : ""}</textarea>
     <p id="sv-error" class="error-text hidden"></p>
     <div class="row mt">
       <button id="sv-save" class="btn btn-primary">Saqlash</button>
       <button id="sv-close" class="btn">Yopish</button>
     </div>`
  );

  overlay.querySelector("#sv-close").addEventListener("click", closeModal);
  overlay.querySelector("#sv-save").addEventListener("click", async () => {
    const body = {
      category: Number(overlay.querySelector("#sv-cat").value),
      name: overlay.querySelector("#sv-name").value.trim(),
      duration_min: Number(overlay.querySelector("#sv-dur").value),
      price: Number(overlay.querySelector("#sv-price").value),
      description: overlay.querySelector("#sv-desc").value.trim(),
    };
    try {
      if (isEdit) {
        await api(`barber/services/${existing.id}/`, { method: "PATCH", body });
      } else {
        await api("barber/services/", { method: "POST", body });
      }
      toast("Xizmat saqlandi", "ok");
      closeModal();
      loadServices();
    } catch (err) {
      const box = overlay.querySelector("#sv-error");
      box.textContent = err.message;
      box.classList.remove("hidden");
    }
  });
}

/* --- Haftalik jadval --- */

async function loadSchedule() {
  try {
    const data = await api("barber/schedule/");
    const rows = data.schedule || [];
    schedule = DAY_NAMES.map((_, weekday) => {
      const found = rows.find((r) => r.weekday === weekday);
      return {
        weekday,
        is_working: Boolean(found && found.is_working),
        start_time: found ? found.start_time.slice(0, 5) : "09:00",
        end_time: found ? found.end_time.slice(0, 5) : "18:00",
      };
    });
    renderSchedule();
  } catch (err) {
    $("schedule-rows").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

function renderSchedule() {
  $("schedule-rows").innerHTML = "";
  schedule.forEach((row, i) => {
    const rowEl = el(
      `<div class="list-item">
         <div class="row-between">
           <label style="margin:0"><input type="checkbox" data-act="work" ${row.is_working ? "checked" : ""}> ${DAY_NAMES[row.weekday]}</label>
           <span class="muted row">
             <input type="time" step="600" data-act="start" value="${row.start_time}" style="width:110px">
             <span>–</span>
             <input type="time" step="600" data-act="end" value="${row.end_time}" style="width:110px">
           </span>
         </div>
       </div>`
    );
    rowEl.querySelector('[data-act="work"]').addEventListener("change", (e) => {
      schedule[i].is_working = e.target.checked;
    });
    rowEl.querySelector('[data-act="start"]').addEventListener("change", (e) => {
      schedule[i].start_time = e.target.value;
    });
    rowEl.querySelector('[data-act="end"]').addEventListener("change", (e) => {
      schedule[i].end_time = e.target.value;
    });
    $("schedule-rows").appendChild(rowEl);
  });
}

async function saveSchedule() {
  // Ishlamaydigan kunlar uchun ham seriya valid (start<end) bo'lishi shart
  const payload = schedule.map((row) => ({
    weekday: row.weekday,
    is_working: row.is_working,
    start_time: row.is_working ? row.start_time : "09:00",
    end_time: row.is_working ? row.end_time : "18:00",
  }));
  for (const row of payload) {
    if (row.is_working && row.start_time >= row.end_time) {
      toast(`${DAY_NAMES[row.weekday]}: boshlanish tugashidan oldin bo'lishi kerak`, "err");
      return;
    }
  }
  try {
    await api("barber/schedule/", { method: "PUT", body: { schedule: payload } });
    toast("Jadval saqlandi", "ok");
    loadSchedule();
  } catch (err) {
    toast(err.message, "err");
  }
}

/* --- Tanaffuslar --- */

async function loadBreaks() {
  try {
    const breaks = await api("barber/schedule/breaks/");
    $("b-empty").classList.toggle("hidden", breaks.length > 0);
    $("b-list").innerHTML = "";
    for (const brk of breaks) {
      const card = el(
        `<div class="list-item">
           <div class="row-between">
             <span>${DAY_NAMES[brk.weekday] ?? "?"} · ${brk.start_time.slice(0, 5)}–${brk.end_time.slice(0, 5)}</span>
             <button class="btn btn-sm btn-danger">O'chirish</button>
           </div>
         </div>`
      );
      card.querySelector("button").addEventListener("click", async () => {
        try {
          await api(`barber/schedule/breaks/${brk.id}/`, { method: "DELETE" });
          toast("Tanaffus o'chirildi", "ok");
          loadBreaks();
        } catch (err) {
          toast(err.message, "err");
        }
      });
      $("b-list").appendChild(card);
    }
  } catch (err) {
    $("b-list").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

async function addBreak() {
  try {
    await api("barber/schedule/breaks/", {
      method: "POST",
      body: {
        weekday: Number($("b-weekday").value),
        start_time: $("b-start").value,
        end_time: $("b-end").value,
      },
    });
    toast("Tanaffus qo'shildi", "ok");
    loadBreaks();
  } catch (err) {
    toast(err.message, "err");
  }
}

/* --- Dam olish kunlari --- */

async function loadDayOffs() {
  try {
    const dayOffs = await api("barber/day-offs/");
    $("d-empty").classList.toggle("hidden", dayOffs.length > 0);
    $("d-list").innerHTML = "";
    for (const dayOff of dayOffs) {
      const card = el(
        `<div class="list-item">
           <div class="row-between">
             <span>${fmtDate(dayOff.date)} ${dayOff.reason ? "· " + dayOff.reason : ""}</span>
             <button class="btn btn-sm btn-danger">O'chirish</button>
           </div>
         </div>`
      );
      card.querySelector("button").addEventListener("click", async () => {
        try {
          await api(`barber/day-offs/${dayOff.id}/`, { method: "DELETE" });
          toast("Dam olish kuni o'chirildi", "ok");
          loadDayOffs();
        } catch (err) {
          toast(err.message, "err");
        }
      });
      $("d-list").appendChild(card);
    }
  } catch (err) {
    $("d-list").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

async function addDayOff() {
  try {
    await api("barber/day-offs/", {
      method: "POST",
      body: { date: $("d-date").value, reason: $("d-reason").value.trim() },
    });
    toast("Dam olish kuni qo'shildi", "ok");
    loadDayOffs();
  } catch (err) {
    toast(err.message, "err");
  }
}

function fmtDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}
