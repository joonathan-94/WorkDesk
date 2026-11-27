"""Respaldos de WorkDesk: la base de datos y los adjuntos en un único paquete comprobable.

Se crean y se comprueban solo por comandos (`backup-create`, `backup-verify` y
`backup-list`): la web no ejecuta respaldos (`docs/12`, fase 8). Módulos:

- `postgres`: dónde están `pg_dump` y `pg_restore` y cómo se les pasa la conexión;
- `package`: el formato del paquete, su manifiesto, su firma y el listado de la carpeta;
- `creation`: crear un respaldo desde una única foto de la base;
- `verification`: comprobar un respaldo sin restaurarlo.
"""

from .creation import BackupResult as BackupResult
from .creation import create_backup as create_backup
from .package import BackupInfo as BackupInfo
from .package import list_backups as list_backups
from .postgres import BackupError as BackupError
from .verification import Verification as Verification
from .verification import verify_backup as verify_backup
