// Mejora progresiva: sin JavaScript el formulario funciona igual,
// solo se pierde el botón para mostrar u ocultar cada contraseña.
document
    .querySelectorAll("[data-password-toggle]")
    .forEach((toggle) => {
        const input = document.getElementById(
            toggle.getAttribute("aria-controls"),
        );

        if (!input) {
            return;
        }

        toggle.addEventListener("click", () => {
            const isVisible = input.type === "text";

            input.type = isVisible ? "password" : "text";

            toggle.textContent = isVisible ? "Mostrar" : "Ocultar";

            toggle.setAttribute("aria-pressed", String(!isVisible));

            toggle.setAttribute(
                "aria-label",
                isVisible ? "Mostrar contraseña" : "Ocultar contraseña",
            );

            input.focus();
        });
    });
