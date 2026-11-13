/* `/notifications/` — xabarnomalar ro'yxati: o'qish, hammasini o'qish, live qo'shilish. */

import { api, el, fmtTime, toast } from "../api.js";
import { redirectIfNotRole } from "./common.js";

const $ = (id) => document.getElementById(id);

init();

function init() {
  if (!redirectIfNotRole(["client", "barber", "salon_admin", "superadmin"])) return;
  $("notif-app").classList.remove("hidden");
  $("read-all-btn").addEventListener("click", readAll);
  load();
  // WS yangi xabar yuborsa — ro'yxat boshiga qo'shamiz
  document.addEventListener("bb:notify", onPush);
}

function onPush(event) {
  const data = event.detail || {};
  if (!data.id) return;
  $("empty").classList.add("hidden");
  $("notif-list").prepend(notificationRow(data));
  toast(data.title || "Yangi xabar", "ok");
}

async function load() {
  $("notif-list").innerHTML = '<p class="loading">Yuklanmoqda...</p>';
  try {
    const data = await api("notifications/");
    const items = data.results || data;
    $("empty").classList.toggle("hidden", items.length > 0);
    $("notif-list").innerHTML = "";
    for (const item of items) {
      $("notif-list").appendChild(notificationRow(item));
    }
  } catch (err) {
    $("notif-list").innerHTML = "";
    toast(err.message, "err");
  }
}

function notificationRow(item) {
  const date = item.created_at ? item.created_at.slice(0, 10).split("-").reverse().join(".") : "";
  const time = item.created_at ? fmtTime(item.created_at.slice(11, 16)) : "";
  const unread = !item.is_read;
  const row = el(
    `<div class="card ${unread ? "highlight" : ""}">
       <div class="row-between">
         <strong>${item.title}</strong>
         <span class="muted">${date} ${time}</span>
       </div>
       <p class="muted">${item.body || ""}</p>
       ${item.link ? `<a href="${item.link}">Ochish →</a>` : ""}
       ${unread ? '<button class="btn btn-sm mt">O\'qilgan qilish</button>' : ""}
     </div>`
  );
  const readBtn = row.querySelector("button");
  if (readBtn) {
    readBtn.addEventListener("click", async () => {
      try {
        await api(`notifications/${item.id}/read/`, { method: "POST" });
        row.classList.remove("highlight");
        readBtn.remove();
        const badge = document.getElementById("nav-unread");
        if (badge && !badge.hidden) {
          const left = Math.max(0, Number(badge.textContent || 0) - 1);
          badge.textContent = String(left);
          badge.hidden = left === 0;
        }
      } catch (err) {
        toast(err.message, "err");
      }
    });
  }
  return row;
}

async function readAll() {
  try {
    const data = await api("notifications/read-all/", { method: "POST" });
    toast(`${data.updated} ta xabar o'qilgan qilindi`, "ok");
    const badge = document.getElementById("nav-unread");
    if (badge) {
      badge.textContent = "0";
      badge.hidden = true;
    }
    load();
  } catch (err) {
    toast(err.message, "err");
  }
}
