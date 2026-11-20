/*
 * Bloqueo temporal de edición de un ticket (docs/10, secciones 71 a 73).
 *
 * Mejora progresiva: sin JavaScript el formulario funciona igual y el bloqueo
 * expira solo. Con JavaScript:
 *
 * - renueva el bloqueo cada `data-lock-heartbeat` segundos mientras la pantalla
 *   está abierta;
 * - lo libera al salir de la pantalla (cancelar, cerrar la pestaña) salvo que
 *   se esté enviando el formulario, porque guardar ya lo libera;
 * - si el servidor dice que otra persona tiene ahora el bloqueo, avisa y
 *   desactiva el botón de guardar (la versión del ticket seguiría protegiendo
 *   el guardado de todos modos).
 */
(function () {
    'use strict';

    var form = document.querySelector('[data-edit-lock]');

    if (!form || !window.fetch) {
        return;
    }

    var renewUrl = form.getAttribute('data-lock-renew-url');
    var releaseUrl = form.getAttribute('data-lock-release-url');
    var token = form.getAttribute('data-lock-csrf');
    var heartbeat = parseInt(form.getAttribute('data-lock-heartbeat'), 10);
    var notice = document.querySelector('[data-edit-lock-notice]');
    var submitting = false;
    var timer = null;

    if (!renewUrl || !releaseUrl || !token || !(heartbeat > 0)) {
        return;
    }

    function lost(message) {
        window.clearInterval(timer);

        if (notice) {
            notice.textContent =
                (message || 'Otra persona está editando este ticket.') +
                ' No podrás guardar tus cambios: copia lo que escribiste y ' +
                'vuelve a abrir la pantalla.';
            notice.classList.remove('d-none');
        }

        var buttons = form.querySelectorAll('button[type="submit"]');

        Array.prototype.forEach.call(buttons, function (button) {
            button.disabled = true;
        });
    }

    function renew() {
        fetch(renewUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': token,
                'Accept': 'application/json'
            }
        })
            .then(function (response) {
                return response.json().then(
                    function (data) {
                        return { status: response.status, data: data };
                    },
                    function () {
                        return { status: response.status, data: null };
                    }
                );
            })
            .then(function (result) {
                if (result.status === 409 && result.data) {
                    lost(result.data.message);
                }
            })
            .catch(function () {
                // Sin red: se vuelve a intentar en el siguiente latido. Si la
                // conexión no vuelve, el bloqueo expira solo.
            });
    }

    timer = window.setInterval(renew, heartbeat * 1000);

    form.addEventListener('submit', function () {
        submitting = true;
    });

    window.addEventListener('pagehide', function () {
        if (submitting) {
            return;
        }

        window.clearInterval(timer);

        if (navigator.sendBeacon) {
            var data = new FormData();

            data.append('csrf_token', token);
            navigator.sendBeacon(releaseUrl, data);
        }
    });
})();
