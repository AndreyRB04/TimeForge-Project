from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tarea(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('pausada', 'Pausada'),
        ('terminada', 'Terminada'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
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