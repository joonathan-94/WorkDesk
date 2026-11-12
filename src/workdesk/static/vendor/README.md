# Dependencias de frontend (vendor)

Bibliotecas de terceros servidas **localmente** desde `static/vendor/`. WorkDesk no depende de ninguna CDN para funcionar (`docs/10_arquitectura.md`, sección 31).

Los archivos se incluyen **sin modificar**, tal como se publican en npm. No se editan a mano: la personalización visual vive en `static/css/theme.css` y `static/css/layout.css`.

## Versiones

| Biblioteca | Versión | Licencia | Origen |
|---|---|---|---|
| Bootstrap | 5.3.8 | MIT | https://www.npmjs.com/package/bootstrap/v/5.3.8 |
| Bootstrap Icons | 1.13.1 | MIT | https://www.npmjs.com/package/bootstrap-icons/v/1.13.1 |

Cada biblioteca incluye su archivo `LICENSE`.

## Archivos y huellas SHA-256

```text
d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede  bootstrap/css/bootstrap.min.css
e4fd49181388c48ec5040bd3fe66f57c29c8e67fcd8502b3354b96ec7ab47cc7  bootstrap/js/bootstrap.bundle.min.js
4620c84ad5ce8602ff65640ed6b7c8b78ebb9e036584f0ebc1ccc88206a4bb51  bootstrap/LICENSE
a5d6387a32ca3baec4d02336b5b3edab50c9dd518355576a011ea3dd9c1d884e  bootstrap-icons/font/bootstrap-icons.min.css
6c75710364a1ca5604267716f6d28997b26319fdb078cf11e0b42ab66ff2ea61  bootstrap-icons/font/fonts/bootstrap-icons.woff2
f55513b7b591cb84a3b87ff0e34ea24d4831d6fedc22e54b911ca64b5b544a15  bootstrap-icons/font/fonts/bootstrap-icons.woff
0fb3e11bd57e896c5a512afd64864d28a37de45d19835016c87ca1ad19ead969  bootstrap-icons/LICENSE
```

Para verificarlas desde `src/workdesk/static/vendor/`:

```bash
sha256sum bootstrap/css/bootstrap.min.css bootstrap/js/bootstrap.bundle.min.js
```

## Notas

- No se incluyen los archivos `.map` (mapas de código fuente). Las herramientas de desarrollo del navegador pueden avisar de que no los encuentran; no afecta al funcionamiento.
- `.gitattributes` marca esta carpeta como `-text` para que Git no convierta sus saltos de línea y las huellas de arriba se mantengan.

## Actualizar una versión

1. Descargar los mismos archivos de la nueva versión desde npm.
2. Reemplazarlos en esta carpeta sin modificarlos.
3. Actualizar la tabla de versiones y las huellas de este documento.
4. Revisar `theme.css` y `layout.css` por si cambió alguna variable de Bootstrap, y comprobar las pantallas.
