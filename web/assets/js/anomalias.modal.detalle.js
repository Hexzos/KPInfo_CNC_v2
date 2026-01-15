// web/assets/js/anomalias.modal.detalle.js
(function () {
  window.KP = window.KP || {};
  window.KP.anomalias = window.KP.anomalias || {};

  function estadoLabel(estado) {
    return estado === "solucionado" ? "Solucionado" : "En revisión";
  }

  function estadoClass(estado) {
    return estado === "solucionado" ? "tag--ok" : "tag--proceso";
  }

  function isExtrasEnabled() {
    return !!(window.KP?.Session?.isExtrasEnabled && window.KP.Session.isExtrasEnabled());
  }

  window.KP.anomalias.initDetalleModal = function () {
    const overlay = document.getElementById("overlay");
    const modal = document.getElementById("modalAnomaliaDetalle");
    const btnX = document.getElementById("btnCerrarModalDetalle");

    const msg = document.getElementById("detalleMsg");
    const btnGuardar = document.getElementById("btnGuardarDetalle");

    const roEstado = document.getElementById("roEstado");
    const selEstado = document.getElementById("detEstado");
    const btnModEstado = document.getElementById("btnModEstado");

    const roSol = document.getElementById("roSolucion");
    const taSol = document.getElementById("detSolucion");
    const btnAddSol = document.getElementById("btnAddSolucion");

    const btnArchivar = document.getElementById("btnArchivarAnomalia");
    const btnRestaurar = document.getElementById("btnRestaurarAnomalia");

    // ✅ NUEVO: edición extras de título + descripción
    const roTitEl = modal?.querySelector?.('[data-det="titulo"]') || null;
    const roDescEl = modal?.querySelector?.('[data-det="descripcion"]') || null;

    let inpTit = modal?.querySelector?.("#detTituloAnomalia") || null;
    let taDesc = modal?.querySelector?.("#detDescAnomalia") || null;

    let btnModTit = modal?.querySelector?.("#btnModTituloAnomalia") || null;
    let btnModDesc = modal?.querySelector?.("#btnModDescAnomalia") || null;

    if (!overlay || !modal) return;
    if (modal.dataset.inited === "1") return;
    modal.dataset.inited = "1";

    let actualId = null;
    let actualEstado = "en_revision";
    let isArchived = false;

    function setMessage(text, isError = false) {
      if (!msg) return;
      msg.style.color = isError ? "#b00020" : "#444";
      msg.textContent = text || "";
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

      const modalCrear = document.getElementById("modalAnomalia");
      const crearAbierto = modalCrear && !modalCrear.hidden;
      overlay.hidden = !crearAbierto;

      setMessage("");
      forceReadOnlyUI();
      document.removeEventListener("keydown", onKey);
    }

    function ensureExtrasTextUI() {
      if (!isExtrasEnabled()) return;

      // Título
      if (roTitEl) {
        if (!inpTit) {
          inpTit = document.createElement("input");
          inpTit.id = "detTituloAnomalia";
          inpTit.className = "det-input";
          inpTit.type = "text";
          inpTit.disabled = true;
          inpTit.hidden = true;
          roTitEl.insertAdjacentElement("afterend", inpTit);
        }

        if (!btnModTit) {
          btnModTit = document.createElement("button");
          btnModTit.id = "btnModTituloAnomalia";
          btnModTit.className = "btn btn--light btn--xs";
          btnModTit.type = "button";
          btnModTit.textContent = "Modificar";
          inpTit.insertAdjacentElement("afterend", btnModTit);

          btnModTit.addEventListener("click", () => {
            if (isArchived) return;
            const extras = isExtrasEnabled();
            if (!extras) return;

            roTitEl.hidden = true;
            inpTit.hidden = false;
            inpTit.disabled = false;
            inpTit.focus();

            if (btnGuardar) btnGuardar.disabled = false;
            setMessage("");
          });
        }
      }

      // Descripción
      if (roDescEl) {
        if (!taDesc) {
          taDesc = document.createElement("textarea");
          taDesc.id = "detDescAnomalia";
          taDesc.className = "det-input";
          taDesc.rows = 4;
          taDesc.disabled = true;
          taDesc.hidden = true;
          roDescEl.insertAdjacentElement("afterend", taDesc);
        }

        if (!btnModDesc) {
          btnModDesc = document.createElement("button");
          btnModDesc.id = "btnModDescAnomalia";
          btnModDesc.className = "btn btn--light btn--xs";
          btnModDesc.type = "button";
          btnModDesc.textContent = "Modificar";
          taDesc.insertAdjacentElement("afterend", btnModDesc);

          btnModDesc.addEventListener("click", () => {
            if (isArchived) return;
            const extras = isExtrasEnabled();
            if (!extras) return;

            roDescEl.hidden = true;
            taDesc.hidden = false;
            taDesc.disabled = false;
            taDesc.focus();

            if (btnGuardar) btnGuardar.disabled = false;
            setMessage("");
          });
        }
      }

      if (btnModTit) btnModTit.hidden = false;
      if (btnModDesc) btnModDesc.hidden = false;
    }

    function forceReadOnlyUI() {
      if (selEstado) {
        selEstado.disabled = true;
        selEstado.hidden = true;
      }
      if (roEstado) roEstado.hidden = false;

      if (taSol) {
        taSol.disabled = true;
        taSol.hidden = true;
      }
      if (roSol) roSol.hidden = false;

      // ✅ nuevo: readonly título/desc
      if (inpTit) {
        inpTit.disabled = true;
        inpTit.hidden = true;
      }
      if (taDesc) {
        taDesc.disabled = true;
        taDesc.hidden = true;
      }
      if (roTitEl) roTitEl.hidden = false;
      if (roDescEl) roDescEl.hidden = false;

      if (btnGuardar) btnGuardar.disabled = true;
    }

    function setExtrasButtonsVisibility() {
      const extras = isExtrasEnabled();

      if (btnArchivar) btnArchivar.hidden = true;
      if (btnRestaurar) btnRestaurar.hidden = true;

      if (!extras) return;

      if (isArchived) {
        if (btnRestaurar) btnRestaurar.hidden = false;
      } else {
        if (btnArchivar) btnArchivar.hidden = false;
      }
    }

    function applyArchivedUI() {
      setExtrasButtonsVisibility();
      forceReadOnlyUI();

      if (btnModEstado) btnModEstado.hidden = true;
      if (btnAddSol) btnAddSol.hidden = true;

      if (btnModTit) btnModTit.hidden = true;
      if (btnModDesc) btnModDesc.hidden = true;

      if (btnGuardar) {
        btnGuardar.hidden = true;
        btnGuardar.disabled = true;
      }

      setMessage("Anomalía archivada: para modificar, primero debe restaurarla.");
    }

    function setLockedUIOperator() {
      setExtrasButtonsVisibility();
      forceReadOnlyUI();

      if (btnModEstado) btnModEstado.hidden = true;
      if (btnAddSol) btnAddSol.hidden = true;

      if (btnModTit) btnModTit.hidden = true;
      if (btnModDesc) btnModDesc.hidden = true;

      if (btnGuardar) {
        btnGuardar.hidden = true;
        btnGuardar.disabled = true;
      }

      setMessage("Anomalía cerrada: no admite modificaciones.");
    }

    function setEditableBaseUI() {
      setExtrasButtonsVisibility();
      forceReadOnlyUI();

      if (btnModEstado) btnModEstado.hidden = false;
      if (btnAddSol) btnAddSol.hidden = false;

      // ✅ extras habilita modificar texto
      const extras = isExtrasEnabled();
      if (btnModTit) btnModTit.hidden = !extras;
      if (btnModDesc) btnModDesc.hidden = !extras;

      if (btnGuardar) {
        btnGuardar.hidden = false;
        btnGuardar.disabled = true;
      }

      setMessage("");
    }

    function enableEstadoEdit() {
      if (isArchived) return;

      const extras = isExtrasEnabled();
      if (!selEstado || !roEstado) return;

      if (!extras && actualEstado !== "en_revision") return;

      roEstado.hidden = true;
      selEstado.hidden = false;
      selEstado.disabled = false;
      selEstado.focus();

      if (btnGuardar) btnGuardar.disabled = false;
      setMessage("");
    }

    function enableSolucionEdit() {
      if (isArchived) return;

      const extras = isExtrasEnabled();
      if (!taSol || !roSol) return;

      if (!extras && actualEstado !== "en_revision") return;

      roSol.hidden = true;
      taSol.hidden = false;
      taSol.disabled = false;
      taSol.focus();

      if (selEstado) {
        selEstado.value = "solucionado";
        enableEstadoEdit();
      }

      if (btnGuardar) btnGuardar.disabled = false;
      setMessage("");
    }

    function fill(data) {
      setMessage("");

      ensureExtrasTextUI();

      modal.querySelectorAll("[data-det]").forEach((el) => {
        const k = el.getAttribute("data-det");
        const v = data?.[k];
        el.textContent = (v === null || v === undefined || v === "") ? "—" : String(v);
      });

      actualEstado = (data?.estado || "en_revision").trim();
      isArchived = Number(data?.es_archivado || 0) === 1;

      if (roEstado) {
        roEstado.textContent = estadoLabel(actualEstado);
        roEstado.className = "det-val estado-pill " + estadoClass(actualEstado);
      }
      if (selEstado) selEstado.value = actualEstado;

      const sol = String(data?.solucion || "").trim();
      if (roSol) roSol.textContent = sol ? sol : "—";
      if (taSol) taSol.value = sol;

      // ✅ prefill título/desc
      const tit = String(data?.titulo || "").trim();
      const desc = String(data?.descripcion || "").trim();
      if (inpTit) inpTit.value = tit;
      if (taDesc) taDesc.value = desc;

      if (isArchived) {
        applyArchivedUI();
        return;
      }

      const extras = isExtrasEnabled();

      if (actualEstado === "solucionado" && !extras) {
        setLockedUIOperator();
        return;
      }

      setEditableBaseUI();
    }

    async function save() {
      if (!actualId) return;

      if (isArchived) return applyArchivedUI();

      const extras = isExtrasEnabled();
      if (!extras && actualEstado === "solucionado") {
        return setLockedUIOperator();
      }

      const estado = (selEstado?.value || "en_revision").trim();
      const solucion = String(taSol?.value || "").trim();

      // ✅ extras: título/desc
      const titulo = extras && inpTit ? String(inpTit.value || "").trim() : null;
      const descripcion = extras && taDesc ? String(taDesc.value || "").trim() : null;

      if (estado === "solucionado" && solucion.length < 10) {
        return setMessage("Para marcar como solucionado, ingrese una solución (mínimo 10 caracteres).", true);
      }
      if (estado === "en_revision" && solucion.length > 0) {
        return setMessage("En revisión no debe registrar solución.", true);
      }

      if (extras && inpTit) {
        if (!titulo || titulo.length < 2) return setMessage("Título inválido (mínimo 2).", true);
      }
      if (extras && taDesc) {
        if (!descripcion || descripcion.length < 10) return setMessage("Descripción inválida (mínimo 10).", true);
      }

      setMessage("Guardando…");

      const body = { estado, solucion: solucion || null };
      if (extras && inpTit) body.titulo = titulo;
      if (extras && taDesc) body.descripcion = descripcion;

      try {
        const res = await window.KP.API.fetchJSON(`/api/anomalias/${actualId}/actualizar`, {
          method: "POST",
          body: JSON.stringify(body),
        });

        fill(res.data || {});
        if (window.KPREFRESH?.refreshAnomalias) await window.KPREFRESH.refreshAnomalias();
      } catch (e) {
        setMessage(e.message || "No fue posible guardar.", true);
      }
    }

    async function archivar() {
      if (!actualId) return;
      if (!isExtrasEnabled()) return setMessage("Se requieren opciones extras activas.", true);
      if (isArchived) return applyArchivedUI();

      setMessage("Archivando…");

      try {
        await window.KP.API.fetchJSON(`/api/anomalias/${actualId}/archivar`, {
          method: "POST",
          body: JSON.stringify({}),
        });

        const res = await window.KP.API.fetchJSON(`/api/anomalias/${actualId}`);
        fill(res.data || {});

        if (window.KPREFRESH?.refreshAnomalias) await window.KPREFRESH.refreshAnomalias();
      } catch (e) {
        setMessage(e.message || "No fue posible archivar.", true);
      }
    }

    async function restaurar() {
      if (!actualId) return;
      if (!isExtrasEnabled()) return setMessage("Se requieren opciones extras activas.", true);
      if (!isArchived) return;

      setMessage("Restaurando…");

      try {
        await window.KP.API.fetchJSON(`/api/anomalias/${actualId}/restaurar`, {
          method: "POST",
          body: JSON.stringify({}),
        });

        const res = await window.KP.API.fetchJSON(`/api/anomalias/${actualId}`);
        fill(res.data || {});

        if (window.KPREFRESH?.refreshAnomalias) await window.KPREFRESH.refreshAnomalias();
      } catch (e) {
        setMessage(e.message || "No fue posible restaurar.", true);
      }
    }

    btnX?.addEventListener("click", close);
    btnModEstado?.addEventListener("click", enableEstadoEdit);
    btnAddSol?.addEventListener("click", enableSolucionEdit);
    btnGuardar?.addEventListener("click", save);

    btnArchivar?.addEventListener("click", archivar);
    btnRestaurar?.addEventListener("click", restaurar);

    window.KP.anomalias.openDetalle = async function (anomaliaId) {
      actualId = Number(anomaliaId || 0);
      if (!actualId) return;

      open();
      setMessage("Cargando…");

      try {
        const res = await window.KP.API.fetchJSON(`/api/anomalias/${actualId}`);
        fill(res.data || {});
      } catch (e) {
        setMessage(e.message || "No fue posible cargar el detalle.", true);
      }
    };
  };
})();
