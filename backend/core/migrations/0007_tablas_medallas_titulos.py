from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_social_y_recompensas'),
    ]

    operations = [
        # Crear tabla MedallaUsuario
        migrations.CreateModel(
            name='MedallaUsuario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('emoji', models.CharField(max_length=10)),
                ('descripcion', models.TextField(blank=True)),
                ('obtenida_en', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medallas', to='auth.user')),
            ],
            options={
                'unique_together': {('user', 'codigo')},
            },
        ),
        # Crear tabla TituloUsuario
        migrations.CreateModel(
            name='TituloUsuario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True)),
                ('obtenido_en', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='titulos', to='auth.user')),
            ],
            options={
                'unique_together': {('user', 'codigo')},
            },
        ),
        # Crear tabla PerfilRecompensas (si no existe)
        migrations.CreateModel(
            name='PerfilRecompensas',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntos', models.IntegerField(default=0)),
                ('nivel', models.IntegerField(default=1)),
                ('titulo_actual', models.CharField(default='🌱 Novato', max_length=100)),
                ('racha_actual', models.IntegerField(default=0)),
                ('racha_maxima', models.IntegerField(default=0)),
                ('ultimo_dia_activo', models.DateField(blank=True, null=True)),
                ('titulo_seleccionado', models.CharField(blank=True, max_length=100)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_recompensas', to='auth.user')),
            ],
        ),
    ]
