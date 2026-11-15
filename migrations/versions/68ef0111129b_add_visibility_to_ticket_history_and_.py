"""add visibility to ticket history and drop event type check

Revision ID: 68ef0111129b
Revises: 399309eba921
Create Date: 2026-11-15 16:22:26.821330

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '68ef0111129b'
down_revision = '399309eba921'
branch_labels = None
depends_on = None


def upgrade():
    # El vocabulario de eventos pasa a controlarlo solo la aplicación
    # (TicketEvent), como ya ocurre con AuditAction: cada evento nuevo dejaba
    # de requerir una migración. Los CHECK de actor se conservan.
    op.drop_constraint(
        'ck_historial_ticket_tipo_evento',
        'historial_ticket',
        type_='check',
    )

    # Alembic no genera estos CHECK por sí solo: se escriben a mano. Los
    # eventos que ya existen quedan PUBLICO (valor por defecto), que es lo
    # que el Solicitante ya veía.
    op.add_column(
        'historial_ticket',
        sa.Column(
            'visibilidad',
            sa.String(length=10),
            server_default='PUBLICO',
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'ck_historial_ticket_visibilidad',
        'historial_ticket',
        "visibilidad IN ('PUBLICO', 'INTERNO')",
    )


def downgrade():
    op.drop_constraint(
        'ck_historial_ticket_visibilidad',
        'historial_ticket',
        type_='check',
    )
    op.drop_column('historial_ticket', 'visibilidad')

    # Si ya existen eventos posteriores a v0.3.0 en el historial, recrear
    # este CHECK falla: es lo esperado, el historial no se borra.
    op.create_check_constraint(
        'ck_historial_ticket_tipo_evento',
        'historial_ticket',
        "tipo_evento IN ('TICKET_CREADO', 'TICKET_MODIFICADO', "
        "'CATEGORIA_CAMBIADA', 'PRIORIDAD_CAMBIADA')",
    )
