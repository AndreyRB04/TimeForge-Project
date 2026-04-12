from django.db import models

class Tarea(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    estimated_time = models.IntegerField() # O el tipo que estés usando
    actual_time = models.IntegerField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)