"""Rutas de los tickets, una por área.

Todas cuelgan del blueprint `tickets` y los nombres de sus endpoints son los de
las funciones (`tickets.detail`, `tickets.edit_ticket`...), así que partir el
archivo no cambió ninguna URL ni ningún `url_for`. Lo que comparten está en
`common.py`. Importar cada módulo aquí es lo que registra sus rutas.
"""

from . import assignment as assignment
from . import attachments as attachments
from . import comments as comments
from . import common as common
from . import creation as creation
from . import detail as detail
from . import editing as editing
from . import listing as listing
from . import relations as relations
from . import requesters as requesters
from . import states as states
