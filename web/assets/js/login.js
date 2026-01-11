// web/assets/js/login.js
(function () {
  window.KP = window.KP || {};
  window.KP.login = window.KP.login || {};

  function setMsg(id, text, isErr = false) {
    const el = document.getElementById(id);
    if (!el) return;
    el.style.color = isErr ? "#b00020" : "";
    el.textContent = text || "";
  }

  async function postJSON(url, body) {
    return window.KP.API.fetchJSON(url, {
      method: "POST",
      body: JSON.stringify(body || {}),
    });
  }

  function show(el, on) {
    if (!el) return;
    el.classList.toggle("is-hidden", !on);
  }

  async function elevateExtras(registro_turno_id) {
    // No repetir
    if (window.KP?.Session?.getExtrasToken?.()) return;

    // Admin (Bearer) => el backend autoriza sin clave (tu api_post.py)
    const payload = await postJSON("/api/extras/elevate", { registro_turno_id });
    const token = payload?.data?.token;

    if (token) {
      window.KP.Session.setExtrasToken(token);
      window.KP.Session.setExtrasEnabled(true);
    }
  }

  async function startTurnoFromAuthUser(authUser) {
    // Requiere backend: /api/registro-turno/iniciar pide operador_nombre/apellido
    const operador_nombre = (authUser?.nombre || "").trim();
    const operador_apellido = (authUser?.apellido || "").trim();

    if (operador_nombre.length < 2 || operador_apellido.length < 2) {
      throw new Error("Perfil de usuario inválido: nombre/apellido requeridos.");
    }

    const res = await postJSON("/api/registro-turno/iniciar", {
      operador_nombre,
      operador_apellido,
    });

    const data = res?.data || {};
    const rid = data.registro_turno_id;
    const rol = data.rol || "operador";

    if (!rid) throw new Error("Respuesta inválida del servidor (sin registro_turno_id).");

    window.KP.Session.setRegistroTurno({
      registro_turno_id: rid,
      operador_nombre,
      operador_apellido,
      fecha: data.fecha,
      rol,
    });

    // Si el backend determinó admin, entrega admin_key (legacy UI admin)
    if (rol === "admin" && data.admin_key) {
      window.KP.Session.setAdminKey(data.admin_key);
    } else {
      window.KP.Session.clearAdminKey && window.KP.Session.clearAdminKey();
    }

    return { rid, rol };
  }

  async function doLogout() {
    try {
      // opcional: invalidar sesión server-side
      await window.KP.API.fetchJSON("/api/auth/logout", { method: "POST", body: "{}" });
    } catch {
      // no bloquea
    }
    window.KP.Session.clear();
  }

  window.KP.login.initLogin = function () {
    const loginForm = document.getElementById("authLoginForm");
    const registerForm = document.getElementById("authRegisterForm");
    const logoutWrap = document.getElementById("logoutWrap");
    const logoutBtn = document.getElementById("logoutBtn");

    const showRegisterBtn = document.getElementById("showRegisterBtn");
    const showLoginBtn = document.getElementById("showLoginBtn");

    if (!loginForm || !registerForm) return;

    // Toggle login/registro
    showRegisterBtn?.addEventListener("click", () => {
      setMsg("authMsg", "");
      setMsg("regMsg", "");
      show(loginForm, false);
      show(registerForm, true);
    });

    showLoginBtn?.addEventListener("click", () => {
      setMsg("authMsg", "");
      setMsg("regMsg", "");
      show(registerForm, false);
      show(loginForm, true);
    });

    // Si ya hay token, muestra “Cerrar sesión” y (opcional) podrías redirigir.
    const hasToken = !!window.KP.Session.getAuthToken?.();
    show(logoutWrap, hasToken);

    logoutBtn?.addEventListener("click", async () => {
      await doLogout();
      show(logoutWrap, false);
      show(registerForm, false);
      show(loginForm, true);
      setMsg("authMsg", "Sesión cerrada.");
    });

    // ----- Login -----
    loginForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      setMsg("authMsg", "");

      const identificador = (document.getElementById("identificador")?.value || "").trim();
      const password = document.getElementById("password")?.value || "";

      if (!identificador || !password) {
        setMsg("authMsg", "Ingrese identificador y contraseña.", true);
        return;
      }

      try {
        setMsg("authMsg", "Validando credenciales…");

        // 1) Auth login
        const res = await postJSON("/api/auth/login", { identificador, password });
        const data = res?.data;

        window.KP.Session.setAuthToken(data?.token);

        // 2) Registro de turno automático con nombre/apellido del usuario autenticado
        setMsg("authMsg", "Iniciando sesión operativa…");
        const { rid, rol } = await startTurnoFromAuthUser(data?.usuario);

        // 3) Admin => extras por defecto + admin panel
        if (rol === "admin") {
          try {
            await elevateExtras(rid);
          } catch {
            // no bloquea
          }
          window.location.href = "/admin.html";
          return;
        }

        // 4) Operador => pedidos
        window.KP.Session.clearExtras && window.KP.Session.clearExtras();
        window.location.href = "/pedidos.html";
      } catch (e) {
        // Si falló login parcial, limpiar para evitar estados intermedios
        window.KP.Session.clear();
        setMsg("authMsg", e?.message || "No fue posible iniciar sesión.", true);
      }
    });

    // ----- Registro abierto (opcional) -----
    registerForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      setMsg("regMsg", "");

      const nombre = (document.getElementById("r_nombre")?.value || "").trim();
      const apellido = (document.getElementById("r_apellido")?.value || "").trim();
      const email = (document.getElementById("r_email")?.value || "").trim();
      const username = (document.getElementById("r_username")?.value || "").trim();
      const password = document.getElementById("r_password")?.value || "";

      if (nombre.length < 2 || apellido.length < 2) {
        setMsg("regMsg", "Nombre y apellido deben tener al menos 2 caracteres.", true);
        return;
      }
      if (!email.includes("@")) {
        setMsg("regMsg", "Email inválido.", true);
        return;
      }
      if ((password || "").length < 8) {
        setMsg("regMsg", "La contraseña debe tener al menos 8 caracteres.", true);
        return;
      }

      try {
        setMsg("regMsg", "Creando cuenta…");
        await postJSON("/api/auth/register", { nombre, apellido, email, username, password });
        setMsg("regMsg", "Cuenta creada. Ahora puedes iniciar sesión.");
      } catch (e) {
        setMsg("regMsg", e?.message || "No fue posible crear la cuenta.", true);
      }
    });
  };
})();
