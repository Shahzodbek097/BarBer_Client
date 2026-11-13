/* `/` — ochiq katalog: viloyat filtri + salon qidirish. */

import { api, el } from "../api.js";

const $ = (id) => document.getElementById(id);
let regionId = "";
let searchTimer = null;

init();

async function init() {
  await loadRegions();
  $("search-btn").addEventListener("click", load);
  $("region-select").addEventListener("change", (e) => {
    regionId = e.target.value;
    load();
  });
  $("search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 350); // yozganda avtomatik qidirish
  });
  await load();
}

async function loadRegions() {
  try {
    const regions = await api("catalog/regions/");
    $("region-select").innerHTML =
      '<option value="">Barcha viloyatlar</option>' +
      regions
        .map((region) => `<option value="${region.id}">${region.name}</option>`)
        .join("");
  } catch (err) {
    // xato bo'lsa ham katalog ishlashda davom etadi
  }
}

async function load() {
  $("empty").classList.add("hidden");
  $("salon-grid").innerHTML = '<p class="loading">Yuklanmoqda...</p>';
  try {
    const data = await api("catalog/salons/", {
      query: { region: regionId, search: $("search-input").value.trim() },
    });
    const salons = data.results || data;
    if (!salons.length) {
      $("salon-grid").innerHTML = "";
      $("empty").classList.remove("hidden");
      return;
    }
    $("salon-grid").innerHTML = "";
    for (const salon of salons) {
      const rating =
        Number(salon.rating_count) > 0
          ? `<span class="rating">★ ${Number(salon.rating_avg).toFixed(1)}</span>`
          : "";
      $("salon-grid").appendChild(
        el(
          `<a class="card clickable" href="/salon/${salon.id}/">
             <h3>${salon.name}</h3>
             <p class="muted">${salon.region_name || ""}${salon.district_name ? " · " + salon.district_name : ""}</p>
             <p class="muted">${salon.address || ""}</p>
             <div class="row-between mt">
               ${rating}
               <span class="muted">${salon.work_time_start ? salon.work_time_start.slice(0, 5) + "–" + salon.work_time_end.slice(0, 5) : ""}</span>
             </div>
           </a>`
        )
      );
    }
  } catch (err) {
    $("salon-grid").innerHTML = "";
    $("empty").textContent = `Xatolik: ${err.message}`;
    $("empty").classList.remove("hidden");
  }
}
