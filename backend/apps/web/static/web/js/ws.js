/* BarBer_Client — WebSocket push (bosqich 6).
 * Rolga qarab /ws/client/{user_id}/ yoki /ws/barber/{user_id}/ ga ulanadi,
 * xabarnomani toast + badge sifatida ko'rsatadi va `bb:notify` hodisasini
 * tarqatadi (sahifa skriptlari ro'yxatni yangilaydi).
 */

import { accessToken, getUser, initHeader, api } from "./api.js";

let socket = null;
let retryTimer = null;

export function connectWS() {
  const user = getUser();
  if (!user || !accessToken()) return;
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  const path = user.role === "barber" ? `ws/barber/${user.id}` : `ws/client/${user.id}`;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/${path}/?token=${accessToken()}`);

  socket.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch {
      return;
    }
    if (!data || !data.type) return;
    // yangi xabar → badge + toast + sahifa hodisasi
    bumpBadge();
    if (data.title) showToast(data.title, data.body);
    document.dispatchEvent(new CustomEvent("bb:notify", { detail: data }));
  };

  socket.onclose = () => {
    if (getUser() && accessToken() && !retryTimer) {
      retryTimer = setTimeout(() => {
        retryTimer = null;
        connectWS();
      }, 5000);
    }
  };
}

function showToast(title, body) {
  // toast api.js'dan aylana importga olib kelmasligi uchun bu yerda minimimal
  const box = document.getElementById("toasts");
  if (!box) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = body ? `${title} — ${body}` : title;
  box.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function bumpBadge() {
  const badge = document.getElementById("nav-unread");
  if (!badge) return;
  const current = Number(badge.textContent || 0) + 1;
  badge.textContent = current;
  badge.hidden = false;
}

export async function refreshBadge() {
  const user = getUser();
  if (!user || !accessToken()) return;
  try {
    const data = await api("notifications/unread-count/");
    const badge = document.getElementById("nav-unread");
    if (badge) {
      badge.textContent = data.unread;
      badge.hidden = data.unread === 0;
    }
  } catch {
    /* badge muhim emas */
  }
}

// Har sahifada: header + WS ulanishi (auth bo'lsa)
initHeader();
connectWS();
refreshBadge();
