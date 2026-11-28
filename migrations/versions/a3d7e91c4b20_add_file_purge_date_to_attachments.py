"""add file purge date to attachments

La retención de archivos eliminados (RF-111, RN-183): cuando borra el archivo físico de un
adjunto que ya se había eliminado, lo anota en `fecha_purga_archivo`. La fila se conserva.
Columna nueva y vacía: no toca datos existentes.

Revision ID: a3d7e91c4b20
Revises: 0c49df07fc88
Create Date: 2026-11-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3d7e91c4b20'
down_revision = '0c49df07fc88'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('archivos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fecha_purga_archivo', sa.DateTime(timezone=True), nullable=True))
        # El autogenerado de Alembic no detecta un CHECK nuevo en una tabla existente.
        batch_op.create_check_constraint(
            'ck_archivos_purga_coherente',
            "fecha_purga_archivo IS NULL OR (NOT activo AND fecha_purga_archivo >= fecha_eliminacion)",
        )


def downgrade():
    with op.batch_alter_table('archivos', schema=None) as batch_op:
        batch_op.drop_constraint('ck_archivos_purga_coherente', type_='check')
        batch_op.drop_column('fecha_purga_archivo')
