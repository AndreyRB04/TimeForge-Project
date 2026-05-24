from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_social_y_recompensas'),
    ]

    operations = [
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
    ]
