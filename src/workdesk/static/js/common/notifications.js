// Contador de la campana de notificaciones (docs/10, sección 89).
// Mejora progresiva: sin JavaScript el contador es el que calculó el servidor al
// cargar la página. Con JavaScript se consulta cada `data-poll-seconds` segundos
// (30 por defecto) y al volver a la pestaña, sin WebSockets.
const bell = document.querySelector("[data-notifications-bell]");

if (bell) {
    const url = bell.dataset.unreadUrl;
    const seconds = Number(bell.dataset.pollSeconds) || 30;
    const badge = bell.querySelector("[data-bell-badge]");
    const label = bell.querySelector("[data-bell-label]");

    let timer = null;

    function show(unread) {
        badge.textContent = unread > 99 ? "99+" : String(unread);
        badge.hidden = unread === 0;
        label.textContent =
            unread === 0 ? "Notificaciones" : `Notificaciones: ${unread} sin leer`;
    }

    async function refresh() {
        try {
            const response = await fetch(url, {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
                cache: "no-store",
            });
            const type = response.headers.get("Content-Type") || "";

            // Si la sesión expiró, el servidor responde 401 (o, si ya no hay sesión, con
            // la pantalla de acceso: no es JSON): se deja de consultar. Esta consulta no
            // cuenta como actividad: no mantiene viva una sesión abandonada.
            if (!response.ok || !type.includes("application/json")) {
                stop();
                return;
            }

            const data = await response.json();

            if (Number.isInteger(data.unread) && data.unread >= 0) {
                show(data.unread);
            }
        } catch {
            // Sin red no pasa nada: se reintenta en el siguiente ciclo.
        }
    }

    function start() {
        if (timer === null) {
            timer = window.setInterval(refresh, seconds * 1000);
        }
    }

    function stop() {
        if (timer !== null) {
            window.clearInterval(timer);
            timer = null;
        }
    }

    // No se consulta con la pestaña oculta; al volver, se actualiza al momento.
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stop();
        } else {
            refresh();
            start();
        }
    });

    if (!document.hidden) {
        start();
    }
}
