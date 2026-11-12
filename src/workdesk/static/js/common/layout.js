// Sidebar colapsable (solo en pantallas grandes; en las demás es offcanvas).
// Mejora progresiva: sin JavaScript la sidebar queda expandida.
const STORAGE_KEY = "workdesk.sidebar.collapsed";

const toggle = document.querySelector("#sidebar-toggle");
const toggleIcon = document.querySelector("#sidebar-toggle-icon");
const toggleLabel = document.querySelector("#sidebar-toggle-label");
const links = document.querySelectorAll(".sidebar-link[data-label]");

function readPreference() {
    try {
        return window.localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
        // El almacenamiento puede estar bloqueado (modo privado, etc.).
        return false;
    }
}

function savePreference(collapsed) {
    try {
        window.localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {
        // Sin almacenamiento, la preferencia solo dura mientras la página.
    }
}

function applyState(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", collapsed);

    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute(
        "aria-label",
        collapsed ? "Expandir menú" : "Contraer menú",
    );

    toggleLabel.textContent = collapsed ? "Expandir" : "Contraer";
    toggleIcon.className = `bi sidebar-link__icon ${
        collapsed ? "bi-chevron-bar-right" : "bi-chevron-bar-left"
    }`;

    // Con la sidebar colapsada solo se ven los iconos: la etiqueta pasa a
    // ser el tooltip de cada opción.
    links.forEach((link) => {
        if (collapsed) {
            link.setAttribute("title", link.dataset.label);
        } else {
            link.removeAttribute("title");
        }
    });
}

if (toggle && toggleIcon && toggleLabel) {
    applyState(readPreference());

    toggle.addEventListener("click", () => {
        const collapsed = !document.body.classList.contains(
            "sidebar-collapsed",
        );

        applyState(collapsed);
        savePreference(collapsed);
    });
}
