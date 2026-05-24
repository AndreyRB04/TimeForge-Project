from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_fcmtoken'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS core_competencia (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                fecha_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
                fecha_fin TIMESTAMP WITH TIME ZONE NOT NULL,
                estado VARCHAR(20) NOT NULL DEFAULT 'activa',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                creador_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                grupo_id INTEGER NOT NULL REFERENCES core_grupo(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS core_participantecompetencia (
                id SERIAL PRIMARY KEY,
                joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                competencia_id INTEGER NOT NULL REFERENCES core_competencia(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                UNIQUE(competencia_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS core_retocompetencia (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(100) NOT NULL,
                descripcion TEXT NOT NULL,
                tipo VARCHAR(20) NOT NULL,
                meta INTEGER NOT NULL,
                puntos_bonus INTEGER NOT NULL DEFAULT 50,
                emoji VARCHAR(10) NOT NULL DEFAULT '🎯',
                competencia_id INTEGER NOT NULL REFERENCES core_competencia(id) ON DELETE CASCADE
            );
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS core_retocompetencia;
            DROP TABLE IF EXISTS core_participantecompetencia;
            DROP TABLE IF EXISTS core_competencia;
            """
        ),
    ]
