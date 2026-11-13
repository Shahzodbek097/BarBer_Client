/* `/panel/` — super admin: statistika + salon moderatsiyasi. */

import { api, el, toast } from "../api.js";
import { redirectIfNotRole, wsReload } from "./common.js";

const $ = (id) => document.getElementById(id);

const SALON_STATUS = {
  pending: "Tasdiqlanmagan",
  approved: "Tasdiqlangan",
  blocked: "Bloklangan",
};

let statusFilter = "";

init();

function init() {
  if (!redirectIfNotRole(["superadmin"])) return;
  $("panel-app").classList.remove("hidden");

  $("salon-tabs").querySelectorAll("[data-status]").forEach((chip) => {
    chip.addEventListener("click", () => {
      statusFilter = chip.dataset.status;
      $("salon-tabs").querySelectorAll("[data-status]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      loadSalons();
    });
  });

  document.addEventListener("bb:notify", wsReload(loadSalons));
  loadStats();
  loadSalons();
}

async function loadStats() {
  try {
    const stats = await api("admin/stats/");
    $("stats").innerHTML = `
      <div class="stat"><div class="num">${stats.users.total}</div><div class="lbl">Foydalanuvchilar</div></div>
      <div class="stat"><div class="num">${stats.barbers_total}</div><div class="lbl">Sartaroshlar</div></div>
      <div class="stat"><div class="num">${stats.salons.by_status.approved}</div><div class="lbl">Tasdiqlangan salon</div></div>
      <div class="stat"><div class="num">${stats.appointments.total}</div><div class="lbl">Barcha navbatlar</div></div>
      <div class="stat"><div class="num">${stats.appointments.today}</div><div class="lbl">Bugungi navbatlar</div></div>
      <div class="stat"><div class="num">${stats.users.by_role.client}</div><div class="lbl">Mijozlar</div></div>
      <div class="stat"><div class="num">${stats.users.by_role.barber}</div><div class="lbl">Sartarosh (user)</div></div>
      <div class="stat"><div class="num">${stats.salons.by_status.pending}</div><div class="lbl">Kutayotgan salon</div></div>
    `;
  } catch (err) {
    $("stats").innerHTML = `<p class="error-text">${err.message}</p>`;
  }
}

async function loadSalons() {
  $("salon-list").innerHTML = '<p class="loading">Yuklanmoqda...</p>';
  try {
    const salons = await api("admin/salons/", { query: { status: statusFilter } });
    $("empty").classList.toggle("hidden", salons.length > 0);
    $("salon-list").innerHTML = "";
    for (const salon of salons) {
      const label = SALON_STATUS[salon.status] || salon.status;
      const tag =
        salon.status === "approved"
          ? `<span class="tag tag-completed">${label}</span>`
          : salon.status === "blocked"
            ? `<span class="tag tag-cancelled">${label}</span>`
            : `<span class="tag tag-pending">${label}</span>`;
      const actions = [];
      if (salon.status !== "approved") {
        actions.push(`<button class="btn btn-sm btn-primary" data-act="approve">Tasdiqlash</button>`);
      }
      if (salon.status !== "blocked") {
        actions.push(`<button class="btn btn-sm btn-danger" data-act="block">Bloklash</button>`);
      }
      const card = el(
        `<div class="list-item">
           <div class="row-between">
             <strong>${salon.name}</strong>
             ${tag}
           </div>
           <p class="muted">${salon.owner_name} · ${salon.region_name || ""}</p>
           <div class="row mt">${actions.join("")}</div>
         </div>`
      );
      card.querySelector('[data-act="approve"]')?.addEventListener("click", async () => {
        try {
          await api(`admin/salons/${salon.id}/approve/`, { method: "POST" });
          toast("Salon tasdiqlandi", "ok");
          loadStats();
          loadSalons();
        } catch (err) {
          toast(err.message, "err");
        }
      });
      card.querySelector('[data-act="block"]')?.addEventListener("click", async () => {
        try {
          await api(`admin/salons/${salon.id}/block/`, { method: "POST" });
          toast("Salon bloklandi", "ok");
          loadStats();
          loadSalons();
        } catch (err) {
          toast(err.message, "err");
        }
      });
      $("salon-list").appendChild(card);
    }
  } catch (err) {
    $("salon-list").innerHTML = "";
    toast(err.message, "err");
  }
}
