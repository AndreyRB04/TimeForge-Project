from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_fcmtoken'),
    ]

    operations = [
        migrations.CreateModel(
            name='Competencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True)),
                ('fecha_inicio', models.DateTimeField()),
                ('fecha_fin', models.DateTimeField()),
                ('estado', models.CharField(choices=[('activa', 'Activa'), ('finalizada', 'Finalizada')], default='activa', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competencias_creadas', to='auth.user')),
                ('grupo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competencias', to='core.grupo')),
            ],
        ),
        migrations.CreateModel(
            name='ParticipanteCompetencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('competencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participantes', to='core.competencia')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='competencias', to='auth.user')),
            ],
            options={
                'unique_together': {('competencia', 'user')},
            },
        ),
        migrations.CreateModel(
            name='RetoCompetencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('tipo', models.CharField(choices=[('tareas', 'Completar tareas'), ('tiempo', 'Trabajar horas'), ('racha', 'Mantener racha'), ('puntos', 'Ganar puntos')], max_length=20)),
                ('meta', models.IntegerField()),
                ('puntos_bonus', models.IntegerField(default=50)),
                ('emoji', models.CharField(default='🎯', max_length=10)),
                ('competencia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos', to='core.competencia')),
            ],
        ),
    ]
