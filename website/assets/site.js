(() => {
  "use strict";

  const menuButton = document.querySelector("[data-menu-button]");
  const navigation = document.querySelector("[data-navigation]");

  const setMenuLabel = (isOpen) => {
    if (!menuButton) return;
    const attribute = isOpen ? "data-menu-close-label" : "data-menu-open-label";
    const label = menuButton.getAttribute(attribute);
    if (label) menuButton.setAttribute("aria-label", label);
  };

  const closeMenu = () => {
    if (!menuButton || !navigation) return;
    menuButton.setAttribute("aria-expanded", "false");
    setMenuLabel(false);
    navigation.classList.remove("open");
    document.body.classList.remove("menu-open");
  };

  if (menuButton && navigation) {
    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      setMenuLabel(!isOpen);
      navigation.classList.toggle("open", !isOpen);
      document.body.classList.toggle("menu-open", !isOpen);
    });

    navigation.addEventListener("click", (event) => {
      if (event.target instanceof HTMLAnchorElement) closeMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
        menuButton.focus();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 860) closeMenu();
    });
  }

  for (const button of document.querySelectorAll("[data-copy-target]")) {
    button.addEventListener("click", async () => {
      const targetId = button.getAttribute("data-copy-target");
      const target = targetId ? document.getElementById(targetId) : null;
      if (!target) return;

      const originalLabel = button.textContent;
      try {
        await navigator.clipboard.writeText(target.textContent ?? "");
        button.textContent = button.getAttribute("data-copied-label") ?? "Copied";
      } catch {
        button.textContent = button.getAttribute("data-error-label") ?? "Copy failed";
      }
      window.setTimeout(() => {
        button.textContent = originalLabel;
      }, 1600);
    });
  }
})();
