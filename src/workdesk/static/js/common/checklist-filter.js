// Mejora progresiva: añade un buscador a una lista de casillas. Sin
// JavaScript el buscador permanece oculto, se ve la lista completa y el
// formulario funciona igual. Filtrar solo oculta casillas: las ya marcadas
// siguen enviándose aunque no se vean.
document.querySelectorAll("[data-checklist]").forEach((checklist) => {
    const search = checklist.querySelector("[data-checklist-search]");
    const items = checklist.querySelectorAll("[data-checklist-item]");
    const emptyMessage = checklist.querySelector("[data-checklist-empty]");

    if (!search) {
        return;
    }

    const input = search.querySelector("input");

    search.hidden = false;

    input.addEventListener("input", () => {
        const query = input.value.trim().toLocaleLowerCase();
        let visible = 0;

        items.forEach((item) => {
            const matches = item.textContent
                .toLocaleLowerCase()
                .includes(query);

            item.hidden = !matches;

            if (matches) {
                visible += 1;
            }
        });

        if (emptyMessage) {
            emptyMessage.hidden = visible > 0;
        }
    });
});
