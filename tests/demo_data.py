"""Los datos de demostración que comparten los tests.

Los 108 tickets de `seed-demo-tickets` (con su equipo, sus grupos, el historial, los
comentarios, los adjuntos, las resoluciones y los períodos de SLA) sirven de datos
realistas para probar cualquier pantalla. Cargarlos cuesta unos 2,6 s, así que los fixtures
`prepared` y `seeded` (en `conftest.py`) los cargan una vez por proceso y cada test parte
de una copia exacta de la base (ver `tests/database.py`).

`NOW` es la hora con la que se cargan: un miércoles a media tarde, con un fin de semana
cercano hacia atrás. Todas las contraseñas del equipo demo son `DEMO_PASSWORD`.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from src.workdesk.extensions import db
from src.workdesk.models import Categoria, Ubicacion
from src.workdesk.seeds import (
    seed_catalogs,
    seed_demo_groups,
    seed_demo_users,
    seed_roles,
)
from src.workdesk.seeds.demo import DEMO_USERS
from src.workdesk.seeds.demo_tickets_data import MARCOLETA, MATTA

DEMO_PASSWORD = "ClaveDemoSegura2026"
ZONE = ZoneInfo("America/Santiago")

# Un miércoles a media tarde: deja hacia atrás un fin de semana cercano.
NOW = datetime(2026, 11, 18, 15, 0, tzinfo=ZONE)

ROLES = {demo.username: demo.rol for demo in DEMO_USERS}
SOLICITANTES = sorted(u for u, rol in ROLES.items() if rol == "SOLICITANTE")


def prepare(app, *, categories=("Redes", "Hardware", "Correo", "Impresoras"),
            locations=(MARCOLETA, MATTA)):
    """Deja la base como la tendría quien siguió el README hasta antes del seed."""
    app.config["APP_TIMEZONE"] = "America/Santiago"

    with app.app_context():
        seed_roles()
        seed_catalogs()
        seed_demo_users(DEMO_PASSWORD)
        seed_demo_groups()

        for order, name in enumerate(categories, start=1):
            db.session.add(Categoria(nombre=name, orden=order))

        for name in locations:
            db.session.add(Ubicacion(nombre=name, tipo="OFICINA"))

        db.session.commit()
