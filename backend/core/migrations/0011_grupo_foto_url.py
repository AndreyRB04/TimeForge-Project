from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_perfil_usuario_recuperacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='grupo',
            name='foto_url',
            field=models.TextField(blank=True),
        ),
    ]
