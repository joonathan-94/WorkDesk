// Mejora progresiva: mantiene al día el contador "n/máximo" de un campo de
// texto. El servidor ya dibuja el número inicial, y el límite se valida igual
// en el servidor con o sin JavaScript.
document.querySelectorAll("[data-counter-for]").forEach((counter) => {
    const field = document.getElementById(counter.dataset.counterFor);
    const max = counter.dataset.max;

    if (!field) {
        return;
    }

    function update() {
        counter.textContent = `${field.value.length}/${max}`;
    }

    field.addEventListener("input", update);
    update();
});
