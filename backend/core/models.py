from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets


class Tarea(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('pausada', 'Pausada'),
        ('terminada', 'Terminada'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    grupo = models.ForeignKey('Grupo', on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    estimated_time = models.IntegerField(default=0)
    actual_time = models.IntegerField(null=True, blank=True, default=0)
    is_completed = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    last_start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def tiempo_total_actual(self):
        if self.estado == 'en_progreso' and self.last_start_time:
            transcurrido = (timezone.now() - self.last_start_time).seconds // 60
            return (self.actual_time or 0) + transcurrido
        return self.actual_time or 0


class UserToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Token de {self.user.username}'


class Amistad(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
    ]

    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_enviadas')
    receptor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_recibidas')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['solicitante', 'receptor']

    def __str__(self):
        return f'{self.solicitante.username} → {self.receptor.username} ({self.estado})'


class CodigoInvitacion(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='codigo_invitacion')
    codigo = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = secrets.token_urlsafe(10)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Código de {self.user.username}: {self.codigo}'


class Grupo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grupos_creados')
    miembros = models.ManyToManyField(User, related_name='grupos', blank=True)
    codigo_acceso = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.codigo_acceso:
            self.codigo_acceso = secrets.token_urlsafe(8)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    def estadisticas_miembro(self, user):
        tareas = Tarea.objects.filter(user=user, grupo=self)
        completadas = tareas.filter(is_completed=True).count()
        tiempo_total = sum(t.actual_time or 0 for t in tareas)
        return {
            'total_tareas': tareas.count(),
            'tareas_completadas': completadas,
            'tiempo_trabajado': tiempo_total,
            'progreso': round((completadas / tareas.count() * 100) if tareas.count() > 0 else 0, 1),
        }
