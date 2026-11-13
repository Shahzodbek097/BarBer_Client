/* Kabinet sahifalari uchun umumiy yordamchilar (bosqich 6). */

import { ROLE_HOME, getUser } from "../api.js";

/** Rol mos kelmasa yo'naltiradi; true — sahifa davom etadi. */
export function redirectIfNotRole(roles) {
  const user = getUser();
  if (!user || !localStorage.getItem("bb_access")) {
    location.replace("/auth/");
    return false;
  }
  if (!roles.includes(user.role)) {
    location.replace(ROLE_HOME[user.role] || "/");
    return false;
  }
  return true;
}

/** WS push'dan keyin ro'yxatni qayta yuklash (debounce bilan). */
export function wsReload(load) {
  let timer = null;
  return () => {
    clearTimeout(timer);
    timer = setTimeout(load, 400);
  };
}
