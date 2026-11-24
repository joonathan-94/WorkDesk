// Mejora progresiva: la casilla de la cabecera marca o desmarca todos los tickets de la
// lista. Sin JavaScript todos vienen marcados y se desmarca uno por uno; el formulario
// funciona igual.
const toggle = document.querySelector("[data-select-all]");

if (toggle) {
    const boxes = () => document.querySelectorAll('input[name="tickets"]');

    const refresh = () => {
        const all = Array.from(boxes());

        toggle.checked = all.length > 0 && all.every((box) => box.checked);
    };

    toggle.addEventListener("change", () => {
        boxes().forEach((box) => {
            box.checked = toggle.checked;
        });
    });

    document.addEventListener("change", (event) => {
        if (event.target.matches('input[name="tickets"]')) {
            refresh();
        }
    });

    refresh();
}
