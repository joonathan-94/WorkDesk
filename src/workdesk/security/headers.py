"""Cabeceras de seguridad y de caché de todas las respuestas.

Se añaden en un único punto (`after_request`) para que ninguna ruta nueva se
quede sin ellas por olvido. Cada una usa `setdefault`: si una ruta ya fijó la
suya (la descarga de un adjunto, por ejemplo), esa manda.

- `X-Content-Type-Options: nosniff`: el navegador respeta el tipo declarado.
- `X-Frame-Options` y `frame-ancestors`: WorkDesk no se puede incrustar en otra
  página (evita el *clickjacking*).
- `Referrer-Policy: same-origin`: no se filtran direcciones internas a otros sitios.
- `Content-Security-Policy`: solo se ejecuta lo que sirve WorkDesk. Todas las
  plantillas cargan sus scripts desde archivos propios (no hay JavaScript en línea) y
  el único `style=` en línea que queda es de datos (el ancho de una barra, el color de
  una prioridad), por eso los estilos admiten `'unsafe-inline'` y los scripts no.
- `Cache-Control: no-store`: las páginas con datos de la sesión no se guardan en
  la caché del navegador (ni se muestran al volver atrás después de cerrar sesión).
  Los archivos estáticos conservan su caché normal.
- `Strict-Transport-Security`: solo con cookies seguras, es decir, cuando WorkDesk
  se sirve por HTTPS (`SESSION_COOKIE_SECURE=true`).
"""

from flask import Flask, request

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)

# Un año, el valor habitual cuando ya se sirve por HTTPS.
HSTS = "max-age=31536000"


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(response):
        headers = response.headers

        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)

        if request.endpoint != "static":
            headers.setdefault("Cache-Control", "no-store")

        if app.config.get("SESSION_COOKIE_SECURE"):
            headers.setdefault("Strict-Transport-Security", HSTS)

        return response
