// Mejora progresiva: sin JavaScript se ven ambas opciones de contraseña
// y el servidor valida según el modo elegido.
const modeInputs = document.querySelectorAll("[data-password-mode]");
const manualField = document.querySelector("#manual-password-field");
const manualInput = document.querySelector("#temporary_password");

function applyPasswordMode({ moveFocus }) {
    const selected = document.querySelector(
        "[data-password-mode]:checked",
    );
    const isManual = selected !== null && selected.value === "manual";

    // Un campo deshabilitado no se envía con el formulario.
    manualField.hidden = !isManual;
    manualInput.disabled = !isManual;

    if (isManual && moveFocus) {
        manualInput.focus();
    }
}

if (modeInputs.length > 0 && manualField && manualInput) {
    modeInputs.forEach((input) => {
        input.addEventListener("change", () => {
            applyPasswordMode({ moveFocus: true });
        });
    });

    applyPasswordMode({ moveFocus: false });
}
