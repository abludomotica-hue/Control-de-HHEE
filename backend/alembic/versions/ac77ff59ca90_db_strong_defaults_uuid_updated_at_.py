from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ac77ff59ca90"
down_revision = "ee8f6ff11981"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) extensión para gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2) id: String(36) -> UUID
    # Si tus IDs existentes son UUID válidos en texto, esto convierte sin perder datos.
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN id TYPE uuid
        USING id::uuid;
        """
    )
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN id SET DEFAULT gen_random_uuid();
        """
    )

    # 3) empleado_objetivo: default en DB
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN empleado_objetivo SET DEFAULT 'MSI Z08SO Team 3 1 Abrahan Rondon (ECC)';
        """
    )

    # 4) incompleto: NOT NULL + default false
    op.execute("UPDATE trabajos SET incompleto = false WHERE incompleto IS NULL;")
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN incompleto SET DEFAULT false,
        ALTER COLUMN incompleto SET NOT NULL;
        """
    )

    # 5) creado_en / actualizado_en NOT NULL (por consistencia)
    op.execute("UPDATE trabajos SET creado_en = now() WHERE creado_en IS NULL;")
    op.execute("UPDATE trabajos SET actualizado_en = now() WHERE actualizado_en IS NULL;")
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN creado_en SET NOT NULL,
        ALTER COLUMN actualizado_en SET NOT NULL;
        """
    )

    # 6) Trigger para actualizado_en
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_actualizado_en()
        RETURNS trigger AS $$
        BEGIN
          NEW.actualizado_en = now();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_set_actualizado_en ON trabajos;")
    op.execute(
        """
        CREATE TRIGGER trg_set_actualizado_en
        BEFORE UPDATE ON trabajos
        FOR EACH ROW
        EXECUTE FUNCTION set_actualizado_en();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_set_actualizado_en ON trabajos;")
    op.execute("DROP FUNCTION IF EXISTS set_actualizado_en();")

    # revert NOT NULL/defaults
    op.execute("ALTER TABLE trabajos ALTER COLUMN creado_en DROP NOT NULL;")
    op.execute("ALTER TABLE trabajos ALTER COLUMN actualizado_en DROP NOT NULL;")

    op.execute("ALTER TABLE trabajos ALTER COLUMN incompleto DROP NOT NULL;")
    op.execute("ALTER TABLE trabajos ALTER COLUMN incompleto DROP DEFAULT;")
    op.execute("ALTER TABLE trabajos ALTER COLUMN empleado_objetivo DROP DEFAULT;")

    # UUID -> String(36)
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN id DROP DEFAULT;
        """
    )
    op.execute(
        """
        ALTER TABLE trabajos
        ALTER COLUMN id TYPE varchar(36)
        USING id::text;
        """
    )
