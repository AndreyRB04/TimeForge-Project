from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_tarea_last_start_time'),
    ]

    operations = [
        migrations.RunSQL(
            """
            -- Tabla CodigoInvitacion
            CREATE TABLE IF NOT EXISTS core_codigoinvitacion (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(20) NOT NULL UNIQUE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE
            );

            -- Tabla Grupo
            CREATE TABLE IF NOT EXISTS core_grupo (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                codigo_acceso VARCHAR(20) NOT NULL UNIQUE DEFAULT '',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                creador_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
            );

            -- Tabla Grupo-Miembros (ManyToMany)
            CREATE TABLE IF NOT EXISTS core_grupo_miembros (
                id SERIAL PRIMARY KEY,
                grupo_id INTEGER NOT NULL REFERENCES core_grupo(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                UNIQUE(grupo_id, user_id)
            );

            -- Campo grupo en Tarea
            ALTER TABLE core_tarea
                ADD COLUMN IF NOT EXISTS grupo_id INTEGER REFERENCES core_grupo(id) ON DELETE SET NULL;

            -- Tabla Amistad
            CREATE TABLE IF NOT EXISTS core_amistad (
                id SERIAL PRIMARY KEY,
                estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                receptor_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                solicitante_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                UNIQUE(solicitante_id, receptor_id)
            );

            -- Tabla PerfilRecompensas
            CREATE TABLE IF NOT EXISTS core_perfilrecompensas (
                id SERIAL PRIMARY KEY,
                puntos INTEGER NOT NULL DEFAULT 0,
                nivel INTEGER NOT NULL DEFAULT 1,
                titulo_actual VARCHAR(100) NOT NULL DEFAULT '',
                racha_actual INTEGER NOT NULL DEFAULT 0,
                racha_maxima INTEGER NOT NULL DEFAULT 0,
                ultimo_dia_activo DATE NULL,
                titulo_seleccionado VARCHAR(100) NOT NULL DEFAULT '',
                user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE
            );

            -- Tabla MedallaUsuario
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

            -- Tabla TituloUsuario
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
            DROP TABLE IF EXISTS core_amistad;
            ALTER TABLE core_tarea DROP COLUMN IF EXISTS grupo_id;
            DROP TABLE IF EXISTS core_grupo_miembros;
            DROP TABLE IF EXISTS core_grupo;
            DROP TABLE IF EXISTS core_codigoinvitacion;
            """
        ),
    ]
