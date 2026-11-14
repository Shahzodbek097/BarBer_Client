/* `/salon/` — salon egasi kabineti: profil tahriri + o'z sartaroshlari. */

import { api, downloadFile, el, toast } from "../api.js";
import { redirectIfNotRole, wsReload } from "./common.js";

const $ = (id) => document.getElementById(id);

const SALON_STATUS = {
  pending: "Tasdiqlanmagan",
  approved: "Tasdiqlangan",
  blocked: "Bloklangan",
};

init();

function init() {
  if (!redirectIfNotRole(["salon_admin"])) return;
  document.addEventListener("bb:notify", wsReload(loadBarbers));
  $("export-btn").addEventListener("click", exportMonth);
  boot();
}

async function exportMonth() {
  $("export-error").classList.add("hidden");
  const now = new Date();
  const from = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  const to = now.toISOString().slice(0, 10);
  try {
    await downloadFile(
      "salon/report/",
      { from, to, format: "xlsx" },
      `salon-report-${from}_${to}.xlsx`
    );
    toast("Hisobot yuklab olindi", "ok");
  } catch (err) {
    const box = $("export-error");
    box.textContent = err.message;
    box.classList.remove("hidden");
  }
}

async function boot() {
  try {
    const salon = await api("salon/profile/");
    enter(salon);
  } catch (err) {
    if (err.status === 404) {
      $("salon-app").classList.remove("hidden");
      $("no-salon").classList.remove("hidden");
      $("guard").innerHTML = "";
    } else {
      $("guard").innerHTML = `<p class="empty">Xatolik: ${err.message}</p>`;
    }
  }
}

function enter(salon) {
  $("guard").innerHTML = "";
  $("salon-app").classList.remove("hidden");
  $("no-salon").classList.add("hidden");
  $("salon-content").classList.remove("hidden");
  $("sp-name").value = salon.name || "";
  $("sp-address").value = salon.address || "";
  $("sp-phone").value = salon.phone || "";
  $("sp-start").value = (salon.work_time_start || "").slice(0, 5);
  $("sp-end").value = (salon.work_time_end || "").slice(0, 5);
  $("sp-desc").value = salon.description || "";
  const st = SALON_STATUS[salon.status] || salon.status;
  $("s-status").innerHTML =
    salon.status === "approved"
      ? `<span class="tag tag-completed">${st}</span>`
      : salon.status === "blocked"
        ? `<span class="tag tag-cancelled">${st}</span>`
        : `<span class="tag tag-pending">${st}</span>`;

  $("sp-save").onclick = save;
  loadBarbers();
}

async function save() {
  try {
    const salon = await api("salon/profile/", {
      method: "PATCH",
      body: {
        name: $("sp-name").value.trim(),
        address: $("sp-address").value.trim(),
        phone: $("sp-phone").value.trim(),
        description: $("sp-desc").value.trim(),
        work_time_start: $("sp-start").value || null,
        work_time_end: $("sp-end").value || null,
      },
    });
    toast("Salon profili saqlandi", "ok");
    enter(salon);
  } catch (err) {
    toast(err.message, "err");
  }
}

async function loadBarbers() {
  try {
    const barbers = await api("salon/barbers/");
    $("barbers-empty").classList.toggle("hidden", barbers.length > 0);
    $("barber-list").innerHTML = "";
    for (const barber of barbers) {
      const rating =
        Number(barber.rating_count) > 0 ? `<span class="rating">★ ${Number(barber.rating_avg).toFixed(1)}</span>` : "";
      const active = barber.is_active_now
        ? '<span class="tag tag-online">Faol</span>'
        : '<span class="muted">Nofaol</span>';
      $("barber-list").appendChild(
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
    $("barbers-empty").textContent = err.message;
    $("barbers-empty").classList.remove("hidden");
  }
}
