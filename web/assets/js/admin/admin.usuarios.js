// web/assets/js/admin/admin.usuarios.js
(function () {
  window.KP = window.KP || {};
  window.KP.admin = window.KP.admin || {};

  const TZ_CHILE = "America/Santiago";

  const SEL = {
    // filtros
    q: "#usrQ",
    rol: "#usrRol",
    activos: "#usrActivos",
    btnBuscar: "#btnUsrBuscar",
    btnLimpiar: "#btnUsrLimpiar",
    btnRefrescar: "#btnUsrRefrescar",
    msg: "#usuariosMsg",

    // tabla
    tbody: "#usuariosTbody",
    btnNuevo: "#btnOpenUsuarioNuevo",

    // modal usuario
    modal: "#modalUsuario",
    modalTitle: "#modalUsuarioTitle",
    modalMsg: "#usuarioModalMsg",
    usrId: "#usrId",
    nombre: "#usrNombre",
    apellido: "#usrApellido",
    email: "#usrEmail",
    username: "#usrUsername",
    rolModal: "#usrRolModal",
    activoModal: "#usrActivo",
    passWrap: "#usrPasswordWrap",
    password: "#usrPassword",
    btnGuardar: "#btnUsrGuardar",

    // overlay
    overlay: "#overlay",

    // pwd change dentro del modal
    pwdBox: "#pwdChangeBox",
    pwdMsg: "#pwdChangeMsg",
    pwdRefresh: "#btnPwdRefresh",
    pwdActiveWrap: "#pwdActiveWrap",
    pwdActiveCreado: "#pwdActiveCreado",
    pwdActiveExpira: "#pwdActiveExpira",
    pwdActiveIP: "#pwdActiveIP",
    pwdApprove: "#btnPwdApprove",
    pwdCancel: "#btnPwdCancel",
    pwdHistTbody: "#pwdHistoryTbody",
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function setMsg(el, text, kind) {
    if (!el) return;
    el.textContent = text || "";
    el.classList.remove("msg--ok", "msg--err");
    if (text) {
      if (kind === "ok") el.classList.add("msg--ok");
      if (kind === "err") el.classList.add("msg--err");
    }
  }

  function clearInlineErrors(scope) {
    if (!scope) return;
    scope.querySelectorAll("[data-err]").forEach((h) => (h.textContent = ""));
  }

  function showInlineError(scope, key, msg) {
    if (!scope) return;
    const el = scope.querySelector(`[data-err="${key}"]`);
    if (el) el.textContent = msg || "";
  }

  function showModal(modal) {
    if (!modal) return;
    modal.hidden = false;
    const ov = $(SEL.overlay);
    if (ov) ov.hidden = false;

    const first = modal.querySelector("#usrNombre, input, select, button, textarea");
    if (first) setTimeout(() => first.focus(), 0);
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.hidden = true;
    const ov = $(SEL.overlay);
    if (ov) ov.hidden = true;
  }

  function normError(err) {
    if (err && err.name === "KPError") {
      return {
        message: err.message || "Solicitud inválida.",
        code: err.code || "",
        fields: err.fields || null,
        status: err.status || null,
      };
    }
    return { message: err?.message || "Error.", code: "", fields: null, status: null };
  }

  async function fetchJSON(url, opts) {
    if (window.KP && window.KP.API && typeof window.KP.API.fetchJSON === "function") {
      try {
        return await window.KP.API.fetchJSON(url, opts);
      } catch (e) {
        const ne = normError(e);
        return { ok: false, error: { code: ne.code || "ERROR", message: ne.message, fields: ne.fields } };
      }
    }

    try {
      const init = opts || {};
      init.method = init.method || "GET";
      init.headers = init.headers || {};
      init.headers["Content-Type"] = "application/json; charset=utf-8";
      const r = await fetch(url, init);
      const j = await r.json().catch(() => ({}));
      return j;
    } catch (e) {
      return { ok: false, error: { code: "ERROR", message: e?.message || "Error." } };
    }
  }

  // =========================
  // Cache usuarios (para resolver "resuelto_por" -> nombre)
  // =========================
  const usersById = new Map();
  let usersFetchedAll = false;

  function cacheUsers(items) {
    (Array.isArray(items) ? items : []).forEach((u) => {
      const id = Number(u?.id || 0);
      if (!id) return;
      usersById.set(id, u);
    });
  }

  function getUserDisplayNameById(id) {
    const u = usersById.get(Number(id));
    if (!u) return null;
    const full = `${u.nombre || ""} ${u.apellido || ""}`.trim();
    if (full) return full;
    if (u.email) return u.email;
    if (u.username) return `@${u.username}`;
    return null;
  }

  async function ensureUsersCacheFor(ids) {
    const missing = (Array.isArray(ids) ? ids : [])
      .map((x) => Number(x || 0))
      .filter((x) => x > 0)
      .filter((x) => !usersById.has(x));

    if (!missing.length) return;
    if (usersFetchedAll) return;

    const res = await apiGetUsuarios({ q: "", rol: "", activos: null });
    if (res && res.ok === false) return;
    const items = res?.data?.items || [];
    cacheUsers(items);
    usersFetchedAll = true;
  }

  // =========================
  // API
  // =========================
  function getFilters() {
    const q = ($(SEL.q)?.value || "").trim();
    const rol = ($(SEL.rol)?.value || "").trim();
    const a = ($(SEL.activos)?.value || "").trim();
    let activos = null;
    if (a === "0") activos = 0;
    if (a === "1") activos = 1;
    return { q, rol, activos };
  }

  async function apiGetUsuarios({ q, rol, activos }) {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (rol) params.set("rol", rol);
    if (activos === 0 || activos === 1) params.set("activos", String(activos));
    const url = "/api/admin/usuarios" + (params.toString() ? `?${params.toString()}` : "");
    return fetchJSON(url);
  }

  async function apiCreateUsuario(dto) {
    return fetchJSON("/api/admin/usuarios/create", {
      method: "POST",
      body: JSON.stringify(dto || {}),
    });
  }

  async function apiUpdateUsuario(dto) {
    return fetchJSON("/api/admin/usuarios/update", {
      method: "POST",
      body: JSON.stringify(dto || {}),
    });
  }

  async function apiToggleUsuario(dto) {
    return fetchJSON("/api/admin/usuarios/toggle", {
      method: "POST",
      body: JSON.stringify(dto || {}),
    });
  }

  // ===== Password change =====
  async function apiPwdStatus(usuario_id) {
    const params = new URLSearchParams();
    params.set("usuario_id", String(usuario_id));
    return fetchJSON(`/api/admin/usuarios/password-change/status?${params.toString()}`);
  }

  async function apiPwdApprove(usuario_id) {
    return fetchJSON("/api/admin/usuarios/password-change/approve", {
      method: "POST",
      body: JSON.stringify({ usuario_id }),
    });
  }

  async function apiPwdCancel(usuario_id) {
    return fetchJSON("/api/admin/usuarios/password-change/cancel", {
      method: "POST",
      body: JSON.stringify({ usuario_id }),
    });
  }

  // =========================
  // UI helpers
  // =========================
  function fillEmpty(tbody, text, colspan = 5) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="${colspan}" class="muted">${escapeHtml(text || "Sin datos.")}</td></tr>`;
  }

  // -------------------------
  // Fechas: SQLite UTC -> Chile
  // -------------------------
  function parseSqliteUtcToDate(s) {
    const raw = (s || "").trim();
    if (!raw) return null;

    if (raw.includes("T")) {
      const d = new Date(raw);
      return isNaN(d.getTime()) ? null : d;
    }

    const m = raw.match(/^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})$/);
    if (!m) return null;

    const y = Number(m[1]);
    const mo = Number(m[2]) - 1;
    const da = Number(m[3]);
    const hh = Number(m[4]);
    const mm = Number(m[5]);
    const ss = Number(m[6]);

    // SQLite datetime('now') suele ser UTC
    const d = new Date(Date.UTC(y, mo, da, hh, mm, ss));
    return isNaN(d.getTime()) ? null : d;
  }

  function fmtChileDateTime(s) {
    const d = parseSqliteUtcToDate(s);
    if (!d) return s || "—";

    try {
      const date = new Intl.DateTimeFormat("es-CL", {
        timeZone: TZ_CHILE,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(d);

      const time = new Intl.DateTimeFormat("es-CL", {
        timeZone: TZ_CHILE,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(d);

      return `${date} ${time}`;
    } catch {
      return s || "—";
    }
  }

  // -------------------------
  // Traducciones UI estados
  // -------------------------
  function estadoToEs(estado) {
    const e = String(estado || "").trim().toUpperCase();
    const map = {
      PENDING: "PENDIENTE",
      APPROVED: "APROBADO",
      CANCELED: "CANCELADO",   // US
      CANCELLED: "CANCELADO",  // UK
      REJECTED: "RECHAZADO",
      EXPIRED: "EXPIRADO",
    };
    return map[e] || (e ? e : "—");
  }

  function renderRow(u) {
    const id = u.id;
    const nombre = `${u.nombre || ""} ${u.apellido || ""}`.trim() || "—";
    const email = u.email || "—";
    const username = u.username ? `@${u.username}` : "";
    const rol = (u.rol || "").toLowerCase();
    const activo = Number(u.activo || 0) === 1;

    const pillRol =
      rol === "admin"
        ? `<span class="estado-pill" title="Rol administrador">admin</span>`
        : `<span class="estado-pill estado-pill--muted" title="Rol operador">operador</span>`;

    const pillActivo =
      activo
        ? `<span class="estado-pill" title="Activo">Sí</span>`
        : `<span class="estado-pill estado-pill--muted" title="Inactivo">No</span>`;

    const dataU = btoa(unescape(encodeURIComponent(JSON.stringify(u || {}))));

    return `
      <tr data-uid="${escapeHtml(id)}" data-u="${dataU}">
        <td>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div>${escapeHtml(nombre)}</div>
            <div class="muted" style="font-size:12px;">ID: ${escapeHtml(id)}</div>
          </div>
        </td>

        <td>
          <div style="display:flex; flex-direction:column; gap:2px;">
            <div>${escapeHtml(email)}</div>
            <div class="muted" style="font-size:12px;">${escapeHtml(username)}</div>
          </div>
        </td>

        <td>${pillRol}</td>
        <td>${pillActivo}</td>

        <td>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button class="btn btn--light btn--xs" type="button" data-action="edit">Editar</button>
          </div>
        </td>
      </tr>
    `;
  }

  function forcePwdBoxFullWidth() {
    const box = $(SEL.pwdBox);
    if (!box) return;
    box.style.gridColumn = "1 / -1";
    box.style.width = "100%";
    box.style.maxWidth = "none";
  }

  function applyPwdBoxTexts() {
    const box = $(SEL.pwdBox);
    if (!box) return;

    // Cambiar el texto descriptivo (2da línea dentro del header del box)
    const desc = box.querySelector(".muted");
    if (desc) {
      desc.textContent =
        "En caso de que el operador solicite cambio de contraseña. Aquí puedes ver estado e historial, y aprobar/cancelar.";
    }

    // Quitar completamente la nota final del modal (si existe)
    const modal = $(SEL.modal);
    if (!modal) return;

    const notes = Array.from(modal.querySelectorAll(".muted.field--wide, .muted"))
      .filter((el) => {
        const t = (el.textContent || "").trim();
        return t === "En edición no se modifica la contraseña. Para un cambio de contraseña se implementará un flujo separado.";
      });

    notes.forEach((el) => (el.hidden = true));
  }

  function setModalMode(mode) {
    const modal = $(SEL.modal);
    if (!modal) return;

    const t = $(SEL.modalTitle);
    if (t) t.textContent = mode === "create" ? "Nuevo usuario" : "Editar usuario";

    const wrap = $(SEL.passWrap);
    if (wrap) wrap.hidden = mode !== "create";

    const pass = $(SEL.password);
    if (pass) pass.value = "";

    const box = $(SEL.pwdBox);
    if (box) box.hidden = mode !== "edit";
    if (mode === "edit") {
      forcePwdBoxFullWidth();
      applyPwdBoxTexts();
    }

    setMsg($(SEL.pwdMsg), "", "");
    const aw = $(SEL.pwdActiveWrap);
    if (aw) aw.hidden = true;
    fillEmpty($(SEL.pwdHistTbody), "Sin datos.", 4);
  }

  function populateModal(u) {
    const modal = $(SEL.modal);
    if (modal) {
      // Guardamos activo original para saber si cambió en el modal
      modal.dataset.origActivo = String(Number(u?.activo || 0) === 1 ? 1 : 0);
    }

    $(SEL.usrId).value = u?.id ? String(u.id) : "";
    $(SEL.nombre).value = u?.nombre || "";
    $(SEL.apellido).value = u?.apellido || "";
    $(SEL.email).value = u?.email || "";
    $(SEL.username).value = u?.username || "";
    $(SEL.rolModal).value = (u?.rol || "operador").toLowerCase() === "admin" ? "admin" : "operador";
    $(SEL.activoModal).value = String(Number(u?.activo || 0) === 1 ? 1 : 0);
  }

  function readModalDto() {
    const uid = ($(SEL.usrId).value || "").trim();
    return {
      id: uid ? Number(uid) : null,
      nombre: ($(SEL.nombre).value || "").trim(),
      apellido: ($(SEL.apellido).value || "").trim(),
      email: ($(SEL.email).value || "").trim(),
      username: ($(SEL.username).value || "").trim(),
      rol: ($(SEL.rolModal).value || "operador").trim(),
      activo: Number(($(SEL.activoModal).value || "1").trim()) === 1 ? 1 : 0,
      password: ($(SEL.password).value || "").trim(),
    };
  }

  function validateModal(dto, mode) {
    const errors = {};
    if (!dto.nombre) errors.usr_nombre = "Nombre requerido.";
    if (!dto.apellido) errors.usr_apellido = "Apellido requerido.";
    if (!dto.email) errors.usr_email = "Email requerido.";
    if (dto.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(dto.email)) errors.usr_email = "Email inválido.";
    if (dto.username && dto.username.length < 3) errors.usr_username = "Username muy corto (mín. 3).";
    if (!dto.rol || !["admin", "operador"].includes(dto.rol)) errors.usr_rol = "Rol inválido.";
    if (![0, 1].includes(dto.activo)) errors.usr_activo = "Estado inválido.";

    if (mode === "create") {
      if (!dto.password) errors.usr_password = "Password requerido.";
      else if (dto.password.length < 8) errors.usr_password = "Mínimo 8 caracteres.";
    }
    return errors;
  }

  // =========================
  // Lista
  // =========================
  async function refreshList() {
    const tbody = $(SEL.tbody);
    const msg = $(SEL.msg);

    setMsg(msg, "", "");
    fillEmpty(tbody, "Cargando...");

    const f = getFilters();
    const res = await apiGetUsuarios(f);

    if (res && res.ok === false) {
      fillEmpty(tbody, "Sin datos.");
      setMsg(msg, res?.error?.message || "No se pudo cargar usuarios.", "err");
      return;
    }

    const items = res?.data?.items || [];
    cacheUsers(items);

    if (!Array.isArray(items) || items.length === 0) {
      fillEmpty(tbody, "Sin resultados.");
      return;
    }

    tbody.innerHTML = items.map(renderRow).join("");
  }

  // =========================
  // Password change UI
  // =========================
  function renderPwdHistory(rows) {
    const tb = $(SEL.pwdHistTbody);
    if (!tb) return;

    const list = Array.isArray(rows) ? rows : [];
    if (!list.length) {
      fillEmpty(tb, "Sin datos.", 4);
      return;
    }

    tb.innerHTML = list
      .map((r) => {
        const estado = estadoToEs(r.estado);
        const creado = fmtChileDateTime(r.creado_en);
        const resuelto = fmtChileDateTime(r.resuelto_en);

        const rid = r.resuelto_por != null ? Number(r.resuelto_por) : 0;
        const nombre = rid ? getUserDisplayNameById(rid) : null;
        const por = nombre ? nombre : rid ? `ID: ${rid}` : "—";

        return `
          <tr>
            <td>${escapeHtml(estado)}</td>
            <td>${escapeHtml(creado)}</td>
            <td>${escapeHtml(resuelto)}</td>
            <td>${escapeHtml(por)}</td>
          </tr>
        `;
      })
      .join("");
  }

  async function loadPwdStatus(usuario_id) {
    const box = $(SEL.pwdBox);
    if (!box || box.hidden) return;

    forcePwdBoxFullWidth();
    applyPwdBoxTexts();

    const msg = $(SEL.pwdMsg);
    const aw = $(SEL.pwdActiveWrap);

    setMsg(msg, "Cargando estado de solicitudes...", "");
    if (aw) aw.hidden = true;

    const res = await apiPwdStatus(usuario_id);

    if (res && res.ok === false) {
      setMsg(msg, res?.error?.message || "No se pudo obtener estado.", "err");
      renderPwdHistory([]);
      return;
    }

    const data = res?.data || {};
    const active = data.active || null;
    const history = data.history || [];

    const ids = (Array.isArray(history) ? history : [])
      .map((h) => Number(h?.resuelto_por || 0))
      .filter((x) => x > 0);
    await ensureUsersCacheFor(ids);

    if (active) {
      if (aw) aw.hidden = false;
      $(SEL.pwdActiveCreado).textContent = fmtChileDateTime(active.creado_en || "");
      $(SEL.pwdActiveExpira).textContent = fmtChileDateTime(active.expira_en || "");
      $(SEL.pwdActiveIP).textContent = active.origen_ip || "—";
      setMsg(msg, "Hay una solicitud pendiente vigente.", "ok");
    } else {
      if (aw) aw.hidden = true;
      setMsg(msg, "No hay solicitudes pendientes vigentes.", "");
    }

    renderPwdHistory(history);
  }

  async function onPwdApprove() {
    const uid = Number(($(SEL.usrId)?.value || "0").trim());
    if (!uid) return;

    if (!confirm("¿Confirmas aprobar y aplicar el cambio de contraseña? Esto cerrará sesión del usuario.")) return;

    const msg = $(SEL.pwdMsg);
    setMsg(msg, "Procesando aprobación...", "");

    const res = await apiPwdApprove(uid);
    if (res && res.ok === false) {
      setMsg(msg, res?.error?.message || "No se pudo aprobar.", "err");
      return;
    }

    setMsg(msg, "Cambio aprobado y aplicado.", "ok");
    await loadPwdStatus(uid);
  }

  async function onPwdCancel() {
    const uid = Number(($(SEL.usrId)?.value || "0").trim());
    if (!uid) return;

    if (!confirm("¿Confirmas cancelar la solicitud pendiente?")) return;

    const msg = $(SEL.pwdMsg);
    setMsg(msg, "Cancelando solicitud...", "");

    const res = await apiPwdCancel(uid);
    if (res && res.ok === false) {
      setMsg(msg, res?.error?.message || "No se pudo cancelar.", "err");
      return;
    }

    setMsg(msg, "Solicitud cancelada.", "ok");
    await loadPwdStatus(uid);
  }

  // =========================
  // Modal open/save
  // =========================
  function openCreate() {
    const modal = $(SEL.modal);
    if (!modal) return;

    clearInlineErrors(modal);
    setMsg($(SEL.modalMsg), "", "");
    setModalMode("create");

    populateModal({
      id: "",
      nombre: "",
      apellido: "",
      email: "",
      username: "",
      rol: "operador",
      activo: 1,
    });

    showModal(modal);
  }

  async function openEdit(u) {
    const modal = $(SEL.modal);
    if (!modal) return;

    clearInlineErrors(modal);
    setMsg($(SEL.modalMsg), "", "");
    setModalMode("edit");

    populateModal(u);
    showModal(modal);

    const uid = Number(u?.id || 0);
    if (uid) await loadPwdStatus(uid);
  }

  function decodeRowUser(row) {
    try {
      const b64 = row.getAttribute("data-u") || "";
      if (!b64) return null;
      const json = decodeURIComponent(escape(atob(b64)));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  async function onSave() {
    const modal = $(SEL.modal);
    const mmsg = $(SEL.modalMsg);
    if (!modal) return;

    clearInlineErrors(modal);
    setMsg(mmsg, "", "");

    const dto = readModalDto();
    const mode = dto.id ? "edit" : "create";

    const errors = validateModal(dto, mode);
    const keys = Object.keys(errors);
    if (keys.length) {
      keys.forEach((k) => showInlineError(modal, k, errors[k]));
      setMsg(mmsg, "Revisa los campos marcados.", "err");
      return;
    }

    // CREATE
    if (mode === "create") {
      const res = await apiCreateUsuario({
        nombre: dto.nombre,
        apellido: dto.apellido,
        email: dto.email,
        password: dto.password,
        username: dto.username || null,
        rol: dto.rol,
        activo: dto.activo,
      });

      if (res && res.ok === false) {
        setMsg(mmsg, res?.error?.message || "No se pudo crear el usuario.", "err");
        return;
      }

      await refreshList();
      hideModal(modal);
      return;
    }

    // EDIT
    // 1) Actualizar datos base (update NO aplica activo en tu backend actual)
    const resUp = await apiUpdateUsuario({
      id: dto.id,
      nombre: dto.nombre,
      apellido: dto.apellido,
      email: dto.email,
      username: dto.username || null,
      rol: dto.rol,
      // activo se maneja por toggle (ver abajo)
    });

    if (resUp && resUp.ok === false) {
      setMsg(mmsg, resUp?.error?.message || "No se pudo actualizar el usuario.", "err");
      return;
    }

    // 2) Si cambió el estado, aplicar toggle usando endpoint dedicado
    const origActivo = Number((modal.dataset.origActivo || "1").trim()) === 1 ? 1 : 0;
    const nextActivo = dto.activo;

    if (origActivo !== nextActivo) {
      const resT = await apiToggleUsuario({ id: dto.id, activo: nextActivo });
      if (resT && resT.ok === false) {
        // OJO: update ya se aplicó, pero toggle falló. Avisamos claro.
        setMsg(
          mmsg,
          resT?.error?.message ||
            "Los datos se guardaron, pero no fue posible cambiar el estado (activo/inactivo).",
          "err"
        );
        // refrescar lista igual para reflejar update
        await refreshList();
        return;
      }
    }

    await refreshList();
    hideModal(modal);
  }

  // =========================
  // Eventos
  // =========================
  async function onTableClick(ev) {
    const btn = ev.target.closest("button[data-action]");
    if (!btn) return;

    const row = btn.closest("tr[data-uid]");
    if (!row) return;

    const action = btn.getAttribute("data-action");
    if (action !== "edit") return;

    const u = decodeRowUser(row);
    if (!u) {
      setMsg($(SEL.msg), "No se pudo leer el usuario seleccionado.", "err");
      return;
    }
    await openEdit(u);
  }

  function bindModalCloseHandlers() {
    document.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-close]");
      if (!btn) return;

      const id = btn.getAttribute("data-close");
      if (!id) return;

      const modal = document.getElementById(id);
      if (modal && modal.classList.contains("modal")) {
        hideModal(modal);
      }
    });

    const ov = $(SEL.overlay);
    if (ov) {
      ov.addEventListener("click", () => {
        const modal = $(SEL.modal);
        if (modal && !modal.hidden) hideModal(modal);
      });
    }

    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      const modal = $(SEL.modal);
      if (modal && !modal.hidden) hideModal(modal);
    });
  }

  function bindFilters() {
    const q = $(SEL.q);
    const btnBuscar = $(SEL.btnBuscar);
    const btnLimpiar = $(SEL.btnLimpiar);
    const btnRefrescar = $(SEL.btnRefrescar);

    q?.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") refreshList();
    });

    btnBuscar?.addEventListener("click", refreshList);
    btnRefrescar?.addEventListener("click", refreshList);

    btnLimpiar?.addEventListener("click", () => {
      if ($(SEL.q)) $(SEL.q).value = "";
      if ($(SEL.rol)) $(SEL.rol).value = "";
      if ($(SEL.activos)) $(SEL.activos).value = "";
      refreshList();
    });
  }

  function bindMain() {
    $(SEL.btnNuevo)?.addEventListener("click", openCreate);
    $(SEL.tbody)?.addEventListener("click", onTableClick);
    $(SEL.btnGuardar)?.addEventListener("click", onSave);

    $(SEL.pwdRefresh)?.addEventListener("click", async () => {
      const uid = Number(($(SEL.usrId)?.value || "0").trim());
      if (uid) await loadPwdStatus(uid);
    });
    $(SEL.pwdApprove)?.addEventListener("click", onPwdApprove);
    $(SEL.pwdCancel)?.addEventListener("click", onPwdCancel);
  }

  function initAll() {
    if (!$(SEL.tbody) || !$(SEL.modal)) return;
    bindFilters();
    bindMain();
    bindModalCloseHandlers();
    refreshList();
  }

  window.KP.admin.usuarios = {
    initAll,
    refresh: refreshList,
  };
})();
