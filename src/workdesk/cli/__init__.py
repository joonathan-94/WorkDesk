"""Comandos propios de la aplicación (`flask --app src.workdesk <comando>`).

Cada módulo registra los comandos de un área; `register_commands` los reúne para la
Application Factory:

- `setup`: la preparación inicial (`seed-roles`, `seed-catalogs` y `create-admin`);
- `demo`: los datos de demostración (`seed-demo`, `seed-demo-tickets` y
  `seed-demo-notifications`), solo para desarrollo;
- `knowledge`: `seed-demo-articles`;
- `sla`: `sla-rebuild` y `sla-status`;
- `scheduling`: `run-scheduler`;
- `backups`: `backup-create`, `backup-verify` y `backup-list`;
- `restore`: `backup-restore`.

Los comandos solo orquestan: la lógica vive en los servicios que llaman.
"""

from flask import Flask

from . import backups, demo, knowledge, restore, scheduling, setup, sla


def register_commands(app: Flask) -> None:
    for area in (setup, demo, knowledge, sla, scheduling, backups, restore):
        area.register(app)
