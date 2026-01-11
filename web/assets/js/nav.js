// web/assets/js/nav.js
(function () {
  window.KP = window.KP || {};
  window.KP.nav = window.KP.nav || {};

  const BODY_OPEN_CLASS = "kp-menu-open";
  const OVERLAY_ID = "menuOverlay";

  function ensureMenuOverlay() {
    let ov = document.getElementById(OVERLAY_ID);
    if (!ov) {
      ov = document.createElement("div");
      ov.id = OVERLAY_ID;
      ov.className = "menu-overlay";
      ov.hidden = true;
      document.body.appendChild(ov);
    }
    return ov;
  }

  function isMobileMode() {
    return window.matchMedia("(max-width: 820px)").matches;
  }

  function openMenu() {
    if (!isMobileMode()) return;
    const ov = ensureMenuOverlay();
    document.body.classList.add(BODY_OPEN_CLASS);
    ov.hidden = false;
  }

  function closeMenu() {
    const ov = document.getElementById(OVERLAY_ID);
    document.body.classList.remove(BODY_OPEN_CLASS);
    if (ov) ov.hidden = true;
  }

  function toggleMenu() {
    if (document.body.classList.contains(BODY_OPEN_CLASS)) closeMenu();
    else openMenu();
  }

  // ✅ Bind seguro: funciona con HTMLElement, Document y Window
  function bindOnce(el, key, eventName, handler, options) {
    if (!el) return;

    // HTMLElement: usa dataset (persistente en DOM)
    if (el instanceof HTMLElement) {
      const dsKey = "kpBound" + key;
      if (el.dataset && el.dataset[dsKey] === "1") return;
      if (el.dataset) el.dataset[dsKey] = "1";
      el.addEventListener(eventName, handler, options);
      return;
    }

    // Document/Window/otros: usa una marca en el propio objeto
    const flag = "__kpBound" + key;
    if (el[flag] === true) return;
    try {
      el[flag] = true; // puede fallar en objetos sellados; si falla, igual no rompe
    } catch (_) {}
    el.addEventListener(eventName, handler, options);
  }

  window.KP.nav.initAll = function () {
    const btn = document.getElementById("btnMenu");
    const ov = ensureMenuOverlay();

    // Burger
    bindOnce(btn, "MenuBtn", "click", () => toggleMenu());

    // Click overlay => cerrar
    bindOnce(ov, "MenuOverlay", "click", () => closeMenu());

    // ESC => cerrar
    bindOnce(document, "MenuEsc", "keydown", (ev) => {
      if (ev.key !== "Escape") return;
      if (document.body.classList.contains(BODY_OPEN_CLASS)) closeMenu();
    });

    // Al navegar desde el menú en móvil, cerrar
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) {
      bindOnce(sidebar, "MenuNav", "click", (ev) => {
        const a = ev.target && ev.target.closest ? ev.target.closest("a.navlink") : null;
        if (!a) return;
        if (isMobileMode()) closeMenu();
      });
    }

    // Si cambia el ancho (rotación), asegurar estado coherente
    bindOnce(window, "MenuResize", "resize", () => {
      if (!isMobileMode()) closeMenu();
    });

    // Estado inicial: cerrado
    closeMenu();
  };

  window.KP.nav.open = openMenu;
  window.KP.nav.close = closeMenu;
})();
