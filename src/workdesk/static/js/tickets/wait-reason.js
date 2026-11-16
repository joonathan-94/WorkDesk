// Mejora progresiva: muestra la explicación libre solo cuando el motivo de
// espera elegido la admite. Sin JavaScript el campo se ve siempre y el
// servidor valida igual (un texto sin un motivo que lo admita se rechaza).
const select = document.querySelector("[data-wait-reason-select]");
const textBlock = document.querySelector("[data-wait-reason-text]");

if (select && textBlock) {
    function update() {
        const option = select.options[select.selectedIndex];
        const allowsText = Boolean(option) && option.dataset.allowsText === "true";

        textBlock.hidden = !allowsText;
    }

    select.addEventListener("change", update);
    update();
}
