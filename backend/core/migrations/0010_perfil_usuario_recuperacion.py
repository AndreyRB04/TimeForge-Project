from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_competencia'),
    ]

    operations = [
        migrations.CreateModel(
            name='PerfilUsuario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto_url', models.TextField(blank=True)),
                ('biografia', models.TextField(blank=True)),
                ('carrera', models.CharField(blank=True, max_length=100)),
                ('meta_diaria', models.IntegerField(default=5)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='perfil_usuario',
                    to='auth.user'
                )),
            ],
        ),
        migrations.CreateModel(
            name='CodigoRecuperacion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=6)),
                ('email', models.EmailField(max_length=254)),
                ('usado', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='codigos_recuperacion',
                    to='auth.user'
                )),
            ],
        ),
    ]
