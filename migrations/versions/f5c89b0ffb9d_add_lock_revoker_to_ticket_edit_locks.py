"""add lock revoker to ticket edit locks

Revision ID: f5c89b0ffb9d
Revises: 1160c24e8d85
Create Date: 2026-11-25 17:15:27.561325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5c89b0ffb9d'
down_revision = '1160c24e8d85'
branch_labels = None
depends_on = None


# El nombre que PostgreSQL da por defecto a la clave foránea (así coincide con el del
# esquema creado desde los modelos y el `downgrade` puede nombrarla).
FOREIGN_KEY = "bloqueos_edicion_tickets_liberado_por_usuario_id_fkey"
CHECK = "ck_bloqueos_edicion_liberador_con_fecha"


def upgrade():
    with op.batch_alter_table("bloqueos_edicion_tickets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("liberado_por_usuario_id", sa.BigInteger(), nullable=True)
        )
        batch_op.create_foreign_key(
            FOREIGN_KEY,
            "usuarios",
            ["liberado_por_usuario_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        # Alembic no detecta las restricciones CHECK: se añade a mano.
        batch_op.create_check_constraint(
            CHECK,
            "liberado_por_usuario_id IS NULL OR fecha_liberacion IS NOT NULL",
        )


def downgrade():
    with op.batch_alter_table("bloqueos_edicion_tickets", schema=None) as batch_op:
        batch_op.drop_constraint(CHECK, type_="check")
        batch_op.drop_constraint(FOREIGN_KEY, type_="foreignkey")
        batch_op.drop_column("liberado_por_usuario_id")
