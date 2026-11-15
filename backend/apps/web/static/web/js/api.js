/* BarBer_Client — umumiy JS yadrosi (bosqich 6).
 * JWT saqlash, fetch o'raychi (401 → refresh → qayta urinish), toast, formatlar.
 */

const ACCESS = "bb_access";
const REFRESH = "bb_refresh";
const USER = "bb_user";

export const STATUS_LABELS = {
  pending: "Kutilmoqda",
  confirmed: "Tasdiqlangan",
  completed: "Bajarildi",
  rejected: "Rad etildi",
  cancelled: "Bekor qilindi",
  no_show: "Kelmadi",
};

export const ROLE_HOME = {
  client: "/c/",
  barber: "/barber/",
  salon_admin: "/salon/",
  superadmin: "/panel/",
};

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER) || "null");
  } catch {
    return null;
  }
}

export function accessToken() {
  return localStorage.getItem(ACCESS) || "";
}

export function saveAuth({ access, refresh, user }) {
  localStorage.setItem(ACCESS, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
  if (user) localStorage.setItem(USER, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
  localStorage.removeItem(USER);
}

export async function refreshTokens() {
  const refresh = localStorage.getItem(REFRESH);
  if (!refresh) throw new Error("auth");
  const res = await fetch("/api/v1/auth/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    clearAuth();
    throw new Error("auth");
  }
  const data = await res.json();
  localStorage.setItem(ACCESS, data.access);
  localStorage.setItem(REFRESH, data.refresh);
  return data.access;
}

export function qs(obj) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(obj || {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, value);
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}

export function detailFrom(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  // DRF field xatolari: {"maydon": ["xato", ...]}
  for (const value of Object.values(data)) {
    if (Array.isArray(value) && value.length) return String(value[0]);
    if (typeof value === "string") return value;
  }
  return "";
}

export async function api(path, { method = "GET", body, query } = {}) {
  let url = `/api/v1/${path.replace(/^\//, "")}${qs(query)}`;
  const doFetch = (token) => {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res = await doFetch(accessToken());
  if (res.status === 401 && accessToken()) {
    try {
      const fresh = await refreshTokens();
      res = await doFetch(fresh);
    } catch {
      /* refresh yaroqsiz — pastda 401 sifatida ishlanadi */
    }
  }

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const err = new Error(detailFrom(data) || `Xatolik (${res.status})`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

/* Fayl yuklab olish (Excel hisobotlar uchun) — JWT bilan, blob sifatida */
export async function downloadFile(path, query, filename) {
  const fetchBlob = () => {
    const headers = {};
    if (accessToken()) headers["Authorization"] = `Bearer ${accessToken()}`;
    return fetch(`/api/v1/${path.replace(/^\//, "")}${qs(query)}`, { headers });
  };
  let res = await fetchBlob();
  if (res.status === 401 && accessToken()) {
    try {
      await refreshTokens();
      res = await fetchBlob();
    } catch {
      /* pastda 401 sifatida ishlanadi */
    }
  }
  if (!res.ok) {
    throw new Error(`Yuklab olishning imkoni bo'lmadi (${res.status})`);
  }
  const blob = await res.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 3000);
}

/* --- UI yordamchilari --- */

export function toast(message, type = "info") {
  const box = document.getElementById("toasts");
  if (!box || !message) return;
  const el = document.createElement("div");
  el.className = `toast ${type === "ok" ? "ok" : type === "err" ? "err" : ""}`.trim();
  el.textContent = message;
  box.appendChild(el);
  // 4.5s'dan keyin .out (fade) — keyin DOM'dan olib tashlanadi
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 320);
  }, 4500);
}

export function el(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html.trim();
  return tpl.content.firstElementChild;
}

export function openModal(contentHtml) {
  closeModal();
  const root = document.getElementById("modal-root");
  const overlay = el(`<div class="modal-overlay"><div class="modal-card">${contentHtml}</div></div>`);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
  root.appendChild(overlay);
  return overlay;
}

export function closeModal() {
  const root = document.getElementById("modal-root");
  if (root) root.innerHTML = "";
}

/* --- Formatlar --- */

export function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}.${m}.${y}`;
}

export function fmtTime(value) {
  return value ? value.slice(0, 5) : "";
}

export function fmtPrice(value) {
  const num = Number(value || 0);
  return `${num.toLocaleString("ru-RU")} so'm`;
}

export function statusTag(status) {
  const label = STATUS_LABELS[status] || status;
  return `<span class="tag tag-${status}">${label}</span>`;
}

export function stars(rating) {
  const n = Math.round(Number(rating || 0));
  return "★".repeat(n) + "☆".repeat(5 - n);
}

/* --- Header: rol bo'yicha menyu + xabarnoma badge --- */

function navLinksFor(role) {
  const badge = `<span id="nav-unread" class="badge" hidden></span>`;
  const links = [{ href: "/", label: "Katalog" }];
  if (role === "client") {
    links.push({ href: "/c/", label: "Navbatlarim" });
    links.push({ href: "/notifications/", label: `Xabarlar${badge}` });
  } else if (role === "barber") {
    links.push({ href: "/barber/", label: "Kabinet" });
    links.push({ href: "/barber/profile/", label: "Profil va jadval" });
    links.push({ href: "/notifications/", label: `Xabarlar${badge}` });
  } else if (role === "salon_admin") {
    links.push({ href: "/salon/", label: "Mening salonim" });
    links.push({ href: "/notifications/", label: `Xabarlar${badge}` });
  } else if (role === "superadmin") {
    links.push({ href: "/panel/", label: "Panel" });
    links.push({ href: "/notifications/", label: `Xabarlar${badge}` });
  }
  return links;
}

export function initHeader() {
  const nav = document.getElementById("nav");
  const userbox = document.getElementById("userbox");
  if (!nav || !userbox) return;
  const user = getUser();
  nav.innerHTML = user
    ? navLinksFor(user.role)
        .map(
          (l) =>
            `<a href="${l.href}" class="${location.pathname === l.href ? "active" : ""}">${l.label}</a>`
        )
        .join("")
    : `<a href="/" class="${location.pathname === "/" ? "active" : ""}">Katalog</a>`;

  userbox.innerHTML = user
    ? `<span class="uname">${user.full_name}</span><button id="logout-btn" class="btn btn-sm">Chiqish</button>`
    : `<a href="/auth/" class="btn btn-sm btn-primary">Kirish</a>`;

  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await api("auth/logout/", { method: "POST", body: { refresh: localStorage.getItem(REFRESH) } });
      } catch {
        /* lokal hisobni baribir tozalaymiz */
      }
      clearAuth();
      location.href = "/";
    });
  }
}

export function requireRole(roles) {
  const user = getUser();
  if (!user || !accessToken()) return false;
  return roles.includes(user.role);
}

export function redirectToHome() {
  const user = getUser();
  location.href = user && ROLE_HOME[user.role] ? ROLE_HOME[user.role] : "/auth/";
}
