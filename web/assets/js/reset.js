// web/assets/js/reset.js
(function () {
  const $ = (s) => document.querySelector(s);

  const form = $("#resetForm");
  const msg = $("#resetMsg");
  const btn = $("#btnReset");

  function setMsg(text) {
    if (!msg) return;
    msg.textContent = text || "";
  }

  function disable(disabled) {
    if (btn) btn.disabled = !!disabled;
  }

  form?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    setMsg("");

    const identificador = ($("#identificador")?.value || "").trim();
    const password = ($("#password")?.value || "").trim();
    const password2 = ($("#password2")?.value || "").trim();

    if (!identificador) return setMsg("Ingrese email o username.");
    if (!password || password.length < 8) return setMsg("La contraseña debe tener al menos 8 caracteres.");
    if (password !== password2) return setMsg("Las contraseñas no coinciden.");

    disable(true);

    try {
      const res = await window.KP.API.fetchJSON("/api/auth/password/forgot", {
        method: "POST",
        body: JSON.stringify({ identificador, password }),
      });

      // Tu backend devuelve mensaje genérico en res.data.message
      setMsg(res?.data?.message || "Solicitud enviada.");
      form.reset();
    } catch (e) {
      // Aun si falla, mantén genérico para no filtrar info
      setMsg("Solicitud enviada. Si corresponde, un administrador deberá aprobarla.");
    } finally {
      disable(false);
    }
  });
})();
