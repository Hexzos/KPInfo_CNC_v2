// web/assets/js/pedidos.modal.detalle.js
(function () {
  window.KP = window.KP || {};
  window.KP.pedidos = window.KP.pedidos || {};

  function estadoLabel(estado) {
    if (estado === "en_proceso") return "En proceso";
    if (estado === "completado") return "Completado";
    if (estado === "cancelado") return "Cancelado";
    return estado || "En proceso";
  }

  function isExtrasEnabled() {
    return !!(window.KP?.Session?.isExtrasEnabled && window.KP.Session.isExtrasEnabled());
  }

  // ✅ helper fecha UI (DD-MM-YYYY)
  function humanDate(v) {
    return (window.KP?.utils?.formatDateDMY && window.KP.utils.formatDateDMY(v)) || (v || "—");
  }

  window.KP.pedidos.initPedidoDetalleModal = function () {
    const overlay = document.getElementById("overlay");
    const modal = document.getElementById("modalPedidoDetalle");
    const btnX = document.getElementById("btnCerrarModalDetalle");

    if (!overlay || !modal) return;

    const msg = document.getElementById("detalleMsg");

    const btnArchivar = document.getElementById("btnArchivarPedido");
    const btnRestaurar = document.getElementById("btnRestaurarPedido");
    const btnGuardar = document.getElementById("btnGuardarDetalle");

    const roUlt = document.getElementById("roUltimaPlancha");
    const roCortes = document.getElementById("roCortesTotales");
    const roEstado = document.getElementById("roEstado");

    const inpUlt = document.getElementById("detUltimaPlancha");
    const inpCortes = document.getElementById("detCortesTotales");
    const selEstado = document.getElementById("detEstado");

    const btnModUlt = document.getElementById("btnModUltima");
    const btnSumarCorte = document.getElementById("btnSumarCorte");
    const btnModEstado = document.getElementById("btnModEstado");

    const roPlanchasEl = modal.querySelector('[data-det="planchas_asignadas"]');
    let inpPlanchas = modal.querySelector("#detPlanchasAsignadas");
    let btnModPlanchas = modal.querySelector("#btnModPlanchasAsignadas");

    // ✅ NUEVO: edición extras de código + descripción
    const roCodigoEl = modal.querySelector('[data-det="codigo_producto"]');
    const roDescEl = modal.querySelector('[data-det="descripcion_producto"]');

    let inpCodigo = modal.querySelector("#detCodigoProducto");
    let taDesc = modal.querySelector("#detDescripcionProducto");

    let btnModCodigo = modal.querySelector("#btnModCodigoProducto");
    let btnModDesc = modal.querySelector("#btnModDescripcionProducto");

    if (modal.dataset.inited === "1") return;
    modal.dataset.inited = "1";

    overlay.hidden = true;
    modal.hidden = true;

    let pedidoActualId = null;

    let isLocked = false;
    let isArchived = false;

    function setMessage(text, isError = false) {
      if (!msg) return;
      msg.style.color = isError ? "#b00020" : "#444";
      msg.textContent = text || "";
    }

    // =========================
    // ✅ Extras: UI edición planchas
    // =========================
    function ensureExtrasPlanchasUI() {
      if (!isExtrasEnabled() || !roPlanchasEl) return;

      if (!inpPlanchas) {
        inpPlanchas = document.createElement("input");
        inpPlanchas.id = "detPlanchasAsignadas";
        inpPlanchas.className = "det-input";
        inpPlanchas.type = "number";
        inpPlanchas.min = "1";
        inpPlanchas.step = "1";
        inpPlanchas.disabled = true;
        inpPlanchas.hidden = true;
        roPlanchasEl.insertAdjacentElement("afterend", inpPlanchas);
      }

      if (!btnModPlanchas) {
        btnModPlanchas = document.createElement("button");
        btnModPlanchas.id = "btnModPlanchasAsignadas";
        btnModPlanchas.className = "btn btn--light btn--xs";
        btnModPlanchas.type = "button";
        btnModPlanchas.textContent = "Modificar";
        inpPlanchas.insertAdjacentElement("afterend", btnModPlanchas);

        btnModPlanchas.addEventListener("click", () => {
          if (isArchived) return;
          if (isLocked) return;
          if (!isExtrasEnabled()) return;
          if (!inpPlanchas) return;

          roPlanchasEl.hidden = true;
          inpPlanchas.hidden = false;
          inpPlanchas.disabled = false;
          inpPlanchas.focus();

          if (btnGuardar) btnGuardar.disabled = false;
        });
      }
    }

    // =========================
    // ✅ NUEVO: Extras UI edición código + descripción
    // =========================
    function ensureExtrasTextFieldsUI() {
      if (!isExtrasEnabled()) return;

      // Código producto
      if (roCodigoEl) {
        if (!inpCodigo) {
          inpCodigo = document.createElement("input");
          inpCodigo.id = "detCodigoProducto";
          inpCodigo.className = "det-input";
          inpCodigo.type = "text";
          inpCodigo.disabled = true;
          inpCodigo.hidden = true;
          roCodigoEl.insertAdjacentElement("afterend", inpCodigo);
        }

        if (!btnModCodigo) {
          btnModCodigo = document.createElement("button");
          btnModCodigo.id = "btnModCodigoProducto";
          btnModCodigo.className = "btn btn--light btn--xs";
          btnModCodigo.type = "button";
          btnModCodigo.textContent = "Modificar";
          inpCodigo.insertAdjacentElement("afterend", btnModCodigo);

          btnModCodigo.addEventListener("click", () => {
            if (isArchived) return;
            if (isLocked) return;
            if (!isExtrasEnabled()) return;

            roCodigoEl.hidden = true;
            inpCodigo.hidden = false;
            inpCodigo.disabled = false;
            inpCodigo.focus();

            if (btnGuardar) btnGuardar.disabled = false;
          });
        }
      }

      // Descripción producto
      if (roDescEl) {
        if (!taDesc) {
          taDesc = document.createElement("textarea");
          taDesc.id = "detDescripcionProducto";
          taDesc.className = "det-input"; // reutiliza estilo base
          taDesc.rows = 4;
          taDesc.disabled = true;
          taDesc.hidden = true;
          roDescEl.insertAdjacentElement("afterend", taDesc);
        }

        if (!btnModDesc) {
          btnModDesc = document.createElement("button");
          btnModDesc.id = "btnModDescripcionProducto";
          btnModDesc.className = "btn btn--light btn--xs";
          btnModDesc.type = "button";
          btnModDesc.textContent = "Modificar";
          taDesc.insertAdjacentElement("afterend", btnModDesc);

          btnModDesc.addEventListener("click", () => {
            if (isArchived) return;
            if (isLocked) return;
            if (!isExtrasEnabled()) return;

            roDescEl.hidden = true;
            taDesc.hidden = false;
            taDesc.disabled = false;
            taDesc.focus();

            if (btnGuardar) btnGuardar.disabled = false;
          });
        }
      }

      // Visibilidad de botones (solo extras)
      if (btnModCodigo) btnModCodigo.hidden = false;
      if (btnModDesc) btnModDesc.hidden = false;
    }

    function lockAllToRO() {
      if (inpUlt) {
        inpUlt.disabled = true;
        inpUlt.hidden = true;
      }
      if (inpCortes) {
        inpCortes.disabled = true;
        inpCortes.hidden = true;
      }
      if (selEstado) {
        selEstado.disabled = true;
        selEstado.hidden = true;
      }
      if (inpPlanchas) {
        inpPlanchas.disabled = true;
        inpPlanchas.hidden = true;
      }

      // ✅ nuevo: lock texto extras
      if (inpCodigo) {
        inpCodigo.disabled = true;
        inpCodigo.hidden = true;
      }
      if (taDesc) {
        taDesc.disabled = true;
        taDesc.hidden = true;
      }

      if (roUlt) roUlt.hidden = false;
      if (roCortes) roCortes.hidden = false;
      if (roEstado) roEstado.hidden = false;
      if (roPlanchasEl) roPlanchasEl.hidden = false;

      if (roCodigoEl) roCodigoEl.hidden = false;
      if (roDescEl) roDescEl.hidden = false;

      if (btnGuardar) btnGuardar.disabled = true;
    }

    function hideEditControls() {
      if (btnModUlt) btnModUlt.hidden = true;
      if (btnSumarCorte) btnSumarCorte.hidden = true;
      if (btnModEstado) btnModEstado.hidden = true;
      if (btnModPlanchas) btnModPlanchas.hidden = true;
      if (btnModCodigo) btnModCodigo.hidden = true;
      if (btnModDesc) btnModDesc.hidden = true;
      if (btnGuardar) btnGuardar.hidden = true;
    }

    function hideArchiveControls() {
      if (btnArchivar) btnArchivar.hidden = true;
      if (btnRestaurar) btnRestaurar.hidden = true;
    }

    function applyUIState(lockedByEstado) {
      const extras = isExtrasEnabled();

      hideArchiveControls();

      if (isArchived) {
        isLocked = true;
        lockAllToRO();
        hideEditControls();

        if (extras && btnRestaurar) btnRestaurar.hidden = false;

        setMessage("Pedido archivado: no se puede modificar. Use “Restaurar” en la lista de archivados.");
        return;
      }

      isLocked = !!lockedByEstado && !extras;

      if (extras && btnArchivar) btnArchivar.hidden = false;

      const hideEdits = isLocked;

      if (btnModUlt) btnModUlt.hidden = hideEdits;
      if (btnSumarCorte) btnSumarCorte.hidden = hideEdits;
      if (btnModEstado) btnModEstado.hidden = hideEdits;

      if (btnModPlanchas) btnModPlanchas.hidden = !extras || hideEdits;
      if (btnModCodigo) btnModCodigo.hidden = !extras || hideEdits;
      if (btnModDesc) btnModDesc.hidden = !extras || hideEdits;

      if (btnGuardar) btnGuardar.hidden = hideEdits;

      lockAllToRO();

      if (lockedByEstado && !extras) setMessage("Pedido cerrado: no admite modificaciones.");
      else setMessage("");
    }

    function enableUltima() {
      if (isArchived) return;
      if (isLocked) return;
      if (!inpUlt || !roUlt) return;

      roUlt.hidden = true;
      inpUlt.hidden = false;
      inpUlt.disabled = false;
      inpUlt.focus();
      if (btnGuardar) btnGuardar.disabled = false;
    }

    function enableEstado() {
      if (isArchived) return;
      if (isLocked) return;
      if (!selEstado || !roEstado) return;

      roEstado.hidden = true;
      selEstado.hidden = false;
      selEstado.disabled = false;
      selEstado.focus();
      if (btnGuardar) btnGuardar.disabled = false;
    }

    function ensureCortesEditable() {
      if (isArchived) return;
      if (isLocked) return;
      if (!inpCortes || !roCortes) return;

      if (inpCortes.hidden) {
        roCortes.hidden = true;
        inpCortes.hidden = false;
      }
      inpCortes.disabled = false;
      if (btnGuardar) btnGuardar.disabled = false;
    }

    function fill(data) {
      ensureExtrasPlanchasUI();
      ensureExtrasTextFieldsUI();

      // Fecha y data-det
      modal.querySelectorAll("[data-det]").forEach((el) => {
        const k = el.getAttribute("data-det");
        const v = data?.[k];

        if (v === null || v === undefined || v === "") {
          el.textContent = "—";
          return;
        }

        const key = String(k || "").toLowerCase();
        const asStr = String(v);
        const looksLikeISODate = /^\d{4}-\d{2}-\d{2}/.test(asStr);
        const isFechaKey = key.startsWith("fecha") || key.includes("_fecha") || key.includes("fecha_");

        if (isFechaKey || looksLikeISODate) el.textContent = humanDate(asStr);
        else el.textContent = asStr;
      });

      const planchas = Number(data?.planchas_asignadas ?? 0);
      const ultima = Number(data?.ultima_plancha_trabajada ?? 0);
      const cortes = Number(data?.cortes_totales ?? 0);
      const estado = (data?.estado || "en_proceso").trim();

      isArchived = Number(data?.es_archivado ?? 0) === 1;

      // ✅ Prefill extras texto
      const codigo = String(data?.codigo_producto ?? "");
      const desc = String(data?.descripcion_producto ?? "");
      if (inpCodigo) inpCodigo.value = codigo;
      if (taDesc) taDesc.value = desc;

      if (inpPlanchas) inpPlanchas.value = String(planchas);

      if (roUlt) roUlt.textContent = String(ultima);
      if (roCortes) roCortes.textContent = String(cortes);

      if (roEstado) {
        roEstado.textContent = estadoLabel(estado);
        roEstado.classList.remove("tag--proceso", "tag--ok", "tag--bad", "tag--neutral");
        if (estado === "completado") roEstado.classList.add("tag--ok");
        else if (estado === "cancelado") roEstado.classList.add("tag--bad");
        else roEstado.classList.add("tag--proceso");
      }

      if (inpUlt) inpUlt.value = String(ultima);
      if (inpCortes) inpCortes.value = String(cortes);
      if (selEstado) selEstado.value = estado;

      const lockedByEstado = estado === "completado" || estado === "cancelado";
      applyUIState(lockedByEstado);

      lockAllToRO();
    }

    function onKey(ev) {
      if (ev.key === "Escape") close();
    }

    function open() {
      overlay.hidden = false;
      modal.hidden = false;
      document.addEventListener("keydown", onKey);
    }

    function close() {
      modal.hidden = true;

      const modalCrear = document.getElementById("modalPedido");
      const crearAbierto = modalCrear && !modalCrear.hidden;
      overlay.hidden = !crearAbierto;

      setMessage("");
      lockAllToRO();
      hideArchiveControls();
      document.removeEventListener("keydown", onKey);
    }

    btnX?.addEventListener("click", close);
    btnModUlt?.addEventListener("click", enableUltima);
    btnModEstado?.addEventListener("click", enableEstado);

    btnSumarCorte?.addEventListener("click", () => {
      if (isArchived) return;
      if (isLocked) return;
      if (!inpCortes) return;

      ensureCortesEditable();
      const cur = Number(inpCortes.value || 0);
      inpCortes.value = String(cur + 1);
      if (roCortes) roCortes.textContent = inpCortes.value;
    });

    async function doArchivar() {
      if (!pedidoActualId) return;
      if (!isExtrasEnabled()) return;

      setMessage("Archivando...");
      try {
        await window.KP.API.fetchJSON(`/api/pedidos/${pedidoActualId}/archivar`, { method: "POST" });

        const res = await window.KP.API.fetchJSON(`/api/pedidos/${pedidoActualId}`);
        fill(res.data || {});
        if (window.KPREFRESH?.refreshPedidos) await window.KPREFRESH.refreshPedidos();
      } catch (e) {
        setMessage(e.message || "No fue posible archivar.", true);
      }
    }

    async function doRestaurar() {
      if (!pedidoActualId) return;
      if (!isExtrasEnabled()) return;

      setMessage("Restaurando...");
      try {
        await window.KP.API.fetchJSON(`/api/pedidos/${pedidoActualId}/restaurar`, { method: "POST" });

        const res = await window.KP.API.fetchJSON(`/api/pedidos/${pedidoActualId}`);
        fill(res.data || {});
        if (window.KPREFRESH?.refreshPedidos) await window.KPREFRESH.refreshPedidos();
      } catch (e) {
        setMessage(e.message || "No fue posible restaurar.", true);
      }
    }

    btnArchivar?.addEventListener("click", doArchivar);
    btnRestaurar?.addEventListener("click", doRestaurar);

    async function save() {
      if (isArchived) return;
      if (isLocked) return;
      if (!pedidoActualId) return;

      const extras = isExtrasEnabled();

      const ultima = Number(inpUlt?.value ?? 0);
      const cortes = Number(inpCortes?.value ?? 0);
      const estado = selEstado?.value || "en_proceso";

      const planchasAsignadas = extras && inpPlanchas ? Number(inpPlanchas.value ?? 0) : null;

      // ✅ nuevo: campos extras editables
      const codigo = extras && inpCodigo ? String(inpCodigo.value || "").trim() : null;
      const descripcion = extras && taDesc ? String(taDesc.value || "").trim() : null;

      if (extras && inpPlanchas) {
        if (!Number.isInteger(planchasAsignadas) || planchasAsignadas <= 0) {
          return setMessage("Planchas asignadas inválidas.", true);
        }
      }

      // validaciones extras básicas (defensivas)
      if (extras && inpCodigo) {
        if (!codigo || codigo.length < 1) return setMessage("Código de producto inválido.", true);
      }
      if (extras && taDesc) {
        if (!descripcion || descripcion.length < 10) return setMessage("Descripción inválida (mínimo 10).", true);
      }

      if (!Number.isInteger(ultima) || ultima < 0) return setMessage("Última plancha inválida.", true);
      if (!Number.isInteger(cortes) || cortes < 0) return setMessage("Cortes inválidos.", true);

      setMessage("Guardando...");

      const body = {
        ultima_plancha_trabajada: ultima,
        cortes_totales: cortes,
        estado: estado,
      };

      if (extras && inpPlanchas) body.planchas_asignadas = planchasAsignadas;
      if (extras && inpCodigo) body.codigo_producto = codigo;
      if (extras && taDesc) body.descripcion_producto = descripcion;

      try {
        const res = await window.KP.API.fetchJSON(`/api/pedidos/${pedidoActualId}/actualizar`, {
          method: "POST",
          body: JSON.stringify(body),
        });

        fill(res.data || {});
        if (window.KPREFRESH?.refreshPedidos) await window.KPREFRESH.refreshPedidos();
      } catch (e) {
        setMessage(e.message || "No fue posible guardar.", true);
      }
    }

    btnGuardar?.addEventListener("click", save);

    window.KP.pedidos.openDetalle = async function (pedidoId) {
      pedidoActualId = pedidoId;
      open();
      setMessage("Cargando...");
      hideArchiveControls();

      try {
        const res = await window.KP.API.fetchJSON(`/api/pedidos/${pedidoId}`);
        fill(res.data || {});
      } catch (e) {
        setMessage(e.message || "No fue posible cargar el detalle.", true);
      }
    };
  };
})();
