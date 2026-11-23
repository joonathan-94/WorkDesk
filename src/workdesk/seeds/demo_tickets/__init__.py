"""Carga de los tickets de demostración (comando `seed-demo-tickets`).

Los datos viven en `demo_tickets_data.py`; aquí está la lógica que los carga.

Cómo trabaja:

- Es opcional e independiente de `seed-demo`, pero necesita que ya estén
  cargados los usuarios demo (`seed-demo`) y los catálogos (`seed-catalogs`).
- No crea categorías ni ubicaciones: las busca por su nombre entre las que ya
  existen. Si falta alguna usa la categoría de respaldo o deja el ticket sin
  ubicación, y lo informa.
- Crea y ajusta los tickets con los servicios reales (`create_ticket`,
  `update_ticket`, `change_priority`, `set_group`, `assign_technician`,
  `add_requester`, `remove_requester`, `add_comment` y `change_state`), así
  que valida, versiona y deja el historial exactamente igual que la
  aplicación.
- Hace un único `commit` al final: o se carga todo o no se carga nada.

Identidad. Cada ticket de la lista tiene una `clave` estable. Al crearlo, los
eventos de su historial se marcan en `contexto` con esa clave y con el número
de paso (0 = creación, 1... = cada ajuste). Esa marca es la única huella que
deja el seed. Gracias a ella un ticket ya cargado se reconoce siempre, aunque
después se le cambie el título (en la lista o a mano), y se sabe qué eventos
son del seed y cuáles no.

Fechas. Los servicios sellan los eventos con la hora actual. Para dar
antigüedad, las fechas se escriben con un `UPDATE` directo, SOLO en las filas
que el propio seed creó (ticket, solicitantes e historial). Es el único lugar
del proyecto que lo hace: el ORM sigue rechazando cualquier modificación
normal del historial y no se añadió ningún parámetro de fecha a los
servicios.

Tiempo laboral. Todo el tiempo del seed corre según un calendario laboral
configurable (`WorkCalendar`, de `worktime.py`, por defecto lunes a viernes de
09:00 a 18:00): `hace_dias` cuenta días laborales, las horas de creación caen
dentro de la jornada y los ajustes avanzan en horas laborales, saltando noches,
fines de semana y feriados. Nada cae fuera del calendario ni en el futuro. El
motor que lo calcula (`BusinessClock`) no es del seed: vive en `worktime.py`
porque lo usará también el SLA.

Volver a ejecutarlo. No duplica nada. Los tickets que ya existen no se
vuelven a crear: se *refrescan*, es decir, se reescriben sus fechas para que
queden relativas al día en que se ejecuta de nuevo (creación, historial,
solicitantes y fecha de modificación). El contenido (título, descripción,
categoría...) no se toca. Si el ticket recibió ediciones a mano después de
cargarse, esos eventos se desplazan junto con él para que el historial siga en
orden y nada quede en el futuro. Los tickets creados a mano, sin la marca, no
se tocan nunca.
"""


from .common import DemoTicketsError as DemoTicketsError
from .common import DemoTicketsResult as DemoTicketsResult
from .loader import seed_demo_tickets as seed_demo_tickets
from .validation import validate_demo_tickets as validate_demo_tickets
