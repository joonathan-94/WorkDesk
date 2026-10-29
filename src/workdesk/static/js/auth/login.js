const passwordInput = document.querySelector("#password");
const passwordToggle = document.querySelector("#password-toggle");

if (passwordInput && passwordToggle) {
    passwordToggle.addEventListener("click", () => {
        const passwordIsVisible = passwordInput.type === "text";

        passwordInput.type = passwordIsVisible
            ? "password"
            : "text";

        passwordToggle.textContent = passwordIsVisible
            ? "Mostrar"
            : "Ocultar";

        passwordToggle.setAttribute(
            "aria-pressed",
            String(!passwordIsVisible),
        );

        passwordToggle.setAttribute(
            "aria-label",
            passwordIsVisible
                ? "Mostrar contraseña"
                : "Ocultar contraseña",
        );

        passwordInput.focus();
    });
}