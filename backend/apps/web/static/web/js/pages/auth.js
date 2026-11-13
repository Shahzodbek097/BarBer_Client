/* /auth/ — kirish va ro'yxatdan o'tish (OTP oqimi).
 * 1) telefon (+998...) → kod yuborish  2) kod → JWT saqlash → rol bo'yicha yo'naltirish.
 * ?next= (faqat same-origin) mavjud bo'lsa, unga qaytadi.
 */

import { api, clearAuth, getUser, ROLE_HOME, saveAuth, toast } from "../api.js";

const $ = (id) => document.getElementById(id);

let mode = "login"; // login | register
let phone = "";

init();

function init() {
  // Ro'yxatdan o'tgan foydalanuvchi kabinetga yo'naladi
  const user = getUser();
  if (user && localStorage.getItem("bb_access")) {
    location.replace(safeNext() || ROLE_HOME[user.role] || "/");
    return;
  }
  clearAuth();

  document.querySelectorAll("#auth-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      mode = tab.dataset.mode;
      document.querySelectorAll("#auth-tabs .tab").forEach((t) => t.classList.toggle("active", t === tab));
      $("auth-title").textContent = mode === "login" ? "Telefon raqamingiz" : "Ro'yxatdan o'tish";
      $("register-fields").classList.toggle("hidden", mode !== "register");
    });
  });

  $("send-code").addEventListener("click", sendCode);
  $("verify-btn").addEventListener("click", verify);
  $("back-btn").addEventListener("click", () => {
    $("step-code").classList.add("hidden");
    $("step-phone").classList.remove("hidden");
  });
}

function safeNext() {
  const raw = new URLSearchParams(location.search).get("next") || "";
  if (raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return "";
}

function showError(id, message) {
  const el = $(id);
  el.textContent = message;
  el.classList.remove("hidden");
}

function showStepPhone() {
  $("step-phone").classList.remove("hidden");
  $("step-code").classList.add("hidden");
}

async function sendCode() {
  ["phone-error", "code-error"].forEach((id) => $(id).classList.add("hidden"));
  phone = $("f-phone").value.trim().replace(/[\s()-]/g, "");

  try {
    let data;
    if (mode === "login") {
      data = await api("auth/login/", { method: "POST", body: { phone } });
    } else {
      data = await api("auth/register/", {
        method: "POST",
        body: {
          phone,
          full_name: $("f-full-name").value.trim(),
          role: $("f-role").value,
        },
      });
    }
    phone = data.phone || phone;
    $("code-hint").textContent = data.detail || "Kod SMS orqali yuborildi.";
    if (data.debug_code) {
      $("code-hint").textContent += ` (test rejimi: kod ${data.debug_code})`;
    }
    $("step-phone").classList.add("hidden");
    $("step-code").classList.remove("hidden");
    $("f-code").focus();
  } catch (err) {
    showError("phone-error", err.message);
  }
}

async function verify() {
  $("code-error").classList.add("hidden");
  const code = $("f-code").value.trim();
  try {
    const data = await api("auth/verify-otp/", {
      method: "POST",
      body: { phone, code, purpose: mode === "login" ? "login" : "registration" },
    });
    saveAuth(data);
    toast("Kirish muvaffaqiyatli!", "ok");

    const user = getUser();
    const pending = sessionStorage.getItem("bb_pending_booking");
    const next = safeNext();
    if (next) {
      location.href = next; // barber_page.js pending navbatni tasdiqlaydi
    } else if (pending) {
      sessionStorage.removeItem("bb_pending_booking");
      try {
        const parsed = JSON.parse(pending);
        if (parsed.return_to && parsed.return_to.startsWith("/")) {
          location.href = parsed.return_to;
          return;
        }
      } catch {
        /* buzuq intent — hisobga olmaymiz */
      }
      location.href = user && ROLE_HOME[user.role] ? ROLE_HOME[user.role] : "/";
    } else {
      location.href = user && ROLE_HOME[user.role] ? ROLE_HOME[user.role] : "/";
    }
  } catch (err) {
    showError("code-error", err.message);
  }
}
