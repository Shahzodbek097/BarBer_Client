/* `/salon/{id}/` — salon sahifasi: ma'lumot + sartaroshlar ro'yxati. */

import { api, el } from "../api.js";

const $ = (id) => document.getElementById(id);
const salonId = Number(location.pathname.split("/")[2]);

init();

async function init() {
  if (!salonId) {
    location.href = "/";
    return;
  }
  await Promise.all([loadSalon(), loadBarbers()]);
}

async function loadSalon() {
  try {
    const salon = await api(`catalog/salons/${salonId}/`);
    const rating =
      Number(salon.rating_count) > 0
        ? `<span class="rating">★ ${Number(salon.rating_avg).toFixed(1)}</span>`
        : "";
    $("salon-header").innerHTML = `
      <h1>${salon.name}</h1>
      <p class="muted">${salon.region_name || ""}${salon.district_name ? " · " + salon.district_name : ""}</p>
      <p>${salon.description || ""}</p>
      <div class="row mt">
        ${rating}
        <span class="muted">${salon.address || ""}</span>
      </div>
      <p class="muted mt">Ish vaqti: ${salon.work_time_start ? salon.work_time_start.slice(0, 5) + "–" + salon.work_time_end.slice(0, 5) : "—"}${salon.phone ? " · Tel: " + salon.phone : ""}</p>
    `;
    document.title = `${salon.name} — BarBer`;
  } catch (err) {
    $("salon-header").innerHTML = `<p class="empty">Salon topilmadi yoki moderatsiyadan o'tmagan.</p>`;
  }
}

async function loadBarbers() {
  try {
    const data = await api("catalog/barbers/", { query: { salon: salonId } });
    const barbers = data.results || data;
    if (!barbers.length) {
      $("empty").classList.remove("hidden");
      return;
    }
    $("barber-grid").innerHTML = "";
    for (const barber of barbers) {
      const rating =
        Number(barber.rating_count) > 0
          ? `<span class="rating">★ ${Number(barber.rating_avg).toFixed(1)}</span>`
          : "";
      const active = barber.is_active_now
        ? '<span class="tag tag-online">Faol</span>'
        : '<span class="muted">Nofaol</span>';
      $("barber-grid").appendChild(
        el(
          `<a class="card clickable" href="/barber/${barber.id}/">
             <div class="row-between">
               <h3>${barber.name}</h3>
               ${active}
             </div>
             <p class="muted">${barber.experience_years} yillik tajriba</p>
             ${barber.specialties && barber.specialties.length ? `<p class="muted">${barber.specialties.join(", ")}</p>` : ""}
             <div class="mt">${rating}</div>
           </a>`
        )
      );
    }
  } catch (err) {
    $("empty").textContent = `Xatolik: ${err.message}`;
    $("empty").classList.remove("hidden");
  }
}
