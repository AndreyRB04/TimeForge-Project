from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_codigoinvitacion_grupo_tarea_grupo_perfilrecompensas_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS core_perfilrecompensas (
                id SERIAL PRIMARY KEY,
                puntos INTEGER NOT NULL DEFAULT 0,
                nivel INTEGER NOT NULL DEFAULT 1,
                titulo_actual VARCHAR(100) NOT NULL DEFAULT '🌱 Novato',
                racha_actual INTEGER NOT NULL DEFAULT 0,
                racha_maxima INTEGER NOT NULL DEFAULT 0,
                ultimo_dia_activo DATE NULL,
                titulo_seleccionado VARCHAR(100) NOT NULL DEFAULT '',
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS core_medallasusuario (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                emoji VARCHAR(10) NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                obtenida_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                UNIQUE(user_id, codigo)
            );

            CREATE TABLE IF NOT EXISTS core_titulouseario (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                obtenido_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                UNIQUE(user_id, codigo)
            );
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS core_titulouseario;
            DROP TABLE IF EXISTS core_medallasusuario;
            DROP TABLE IF EXISTS core_perfilrecompensas;
            """
        ),
    ]
