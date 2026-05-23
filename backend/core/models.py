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
# ── SISTEMA DE RECOMPENSAS ─────────────────────────────────────────────────────

NIVELES = [
    (1,   0,     'Novato',              '🌱', 'Iniciando el camino'),
    (2,   50,    'Aprendiz',            '📚', 'Aprendiendo a organizarse'),
    (3,   150,   'Enfocado',            '🎯', 'Con la mente clara'),
    (4,   300,   'Constante',           '⚡', 'La constancia es tu fuerza'),
    (5,   500,   'Productivo',          '🚀', 'Productividad en ascenso'),
    (6,   800,   'Disciplinado',        '🔥', 'El fuego no se apaga'),
    (7,   1200,  'Experto',             '💡', 'Ideas que se convierten en logros'),
    (8,   1800,  'Estratega',           '🧠', 'Planeas antes de actuar'),
    (9,   2500,  'Maestro',             '🏅', 'Dominas tu tiempo'),
    (10,  3500,  'Leyenda',             '👑', 'Pocos llegan aquí'),
    (11,  5000,  'Élite',               '💎', 'En la cima de la productividad'),
    (12,  7000,  'Maestro del Tiempo',  '⏰', 'El tiempo te obedece'),
]

MEDALLAS_CONFIG = [
    {
        'codigo': 'primera_tarea',
        'nombre': 'Primera Tarea',
        'descripcion': 'Completaste tu primera tarea',
        'emoji': '✅',
        'puntos_requeridos': 0,
        'tipo': 'tarea',
        'cantidad_requerida': 1,
    },
    {
        'codigo': 'racha_3',
        'nombre': 'Racha de Fuego',
        'descripcion': '3 días activos seguidos',
        'emoji': '🔥',
        'tipo': 'racha',
        'cantidad_requerida': 3,
    },
    {
        'codigo': 'racha_7',
        'nombre': 'Semana Perfecta',
        'descripcion': '7 días activos seguidos',
        'emoji': '🌟',
        'tipo': 'racha',
        'cantidad_requerida': 7,
    },
    {
        'codigo': 'racha_30',
        'nombre': 'Imparable',
        'descripcion': '30 días activos seguidos',
        'emoji': '💪',
        'tipo': 'racha',
        'cantidad_requerida': 30,
    },
    {
        'codigo': 'tareas_10',
        'nombre': 'Productivo',
        'descripcion': '10 tareas completadas',
        'emoji': '🎯',
        'tipo': 'tarea',
        'cantidad_requerida': 10,
    },
    {
        'codigo': 'tareas_50',
        'nombre': 'Incansable',
        'descripcion': '50 tareas completadas',
        'emoji': '⚡',
        'tipo': 'tarea',
        'cantidad_requerida': 50,
    },
    {
        'codigo': 'tareas_100',
        'nombre': 'Centurión',
        'descripcion': '100 tareas completadas',
        'emoji': '🏆',
        'tipo': 'tarea',
        'cantidad_requerida': 100,
    },
    {
        'codigo': 'tiempo_60',
        'nombre': 'Una Hora',
        'descripcion': '60 minutos trabajados',
        'emoji': '⏱️',
        'tipo': 'tiempo',
        'cantidad_requerida': 60,
    },
    {
        'codigo': 'tiempo_600',
        'nombre': 'Dedicado',
        'descripcion': '10 horas trabajadas',
        'emoji': '⌚',
        'tipo': 'tiempo',
        'cantidad_requerida': 600,
    },
    {
        'codigo': 'tiempo_3000',
        'nombre': 'Maestro del Tiempo',
        'descripcion': '50 horas trabajadas',
        'emoji': '👑',
        'tipo': 'tiempo',
        'cantidad_requerida': 3000,
    },
    {
        'codigo': 'primer_grupo',
        'nombre': 'Equipo',
        'descripcion': 'Te uniste a tu primer grupo',
        'emoji': '👥',
        'tipo': 'grupo',
        'cantidad_requerida': 1,
    },
    {
        'codigo': 'primer_amigo',
        'nombre': 'Sociable',
        'descripcion': 'Agregaste tu primer amigo',
        'emoji': '🤝',
        'tipo': 'amigo',
        'cantidad_requerida': 1,
    },
]

TITULOS = [
    {'codigo': 'madrugador',    'nombre': '🌅 Madrugador',       'descripcion': 'Completa 5 tareas antes de las 8AM'},
    {'codigo': 'nocturno',      'nombre': '🌙 Búho Nocturno',    'descripcion': 'Completa 5 tareas después de las 10PM'},
    {'codigo': 'velocista',     'nombre': '⚡ Velocista',        'descripcion': 'Completa una tarea en menos de 5 minutos'},
    {'codigo': 'perfeccionista','nombre': '💎 Perfeccionista',   'descripcion': 'Completa 10 tareas exactamente a tiempo'},
    {'codigo': 'social',        'nombre': '👑 Líder Social',     'descripcion': 'Tiene 5 o más amigos'},
    {'codigo': 'fundador',      'nombre': '🏗️ Fundador',         'descripcion': 'Creó su primer grupo'},
]


class PerfilRecompensas(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_recompensas')
    puntos = models.IntegerField(default=0)
    nivel = models.IntegerField(default=1)
    titulo_actual = models.CharField(max_length=100, default='🌱 Novato')
    racha_actual = models.IntegerField(default=0)
    racha_maxima = models.IntegerField(default=0)
    ultimo_dia_activo = models.DateField(null=True, blank=True)
    titulo_seleccionado = models.CharField(max_length=100, blank=True)

    def nombre_nivel(self):
        for nivel_num, puntos_min, nombre, emoji, _ in NIVELES:
            if self.nivel == nivel_num:
                return f'{emoji} {nombre} Nivel {self.nivel}'
        return f'Nivel {self.nivel}'

    def puntos_siguiente_nivel(self):
        for nivel_num, puntos_min, _, _, _ in NIVELES:
            if nivel_num == self.nivel + 1:
                return puntos_min
        return None

    def progreso_nivel(self):
        puntos_actual = 0
        puntos_siguiente = self.puntos_siguiente_nivel()
        for nivel_num, puntos_min, _, _, _ in NIVELES:
            if nivel_num == self.nivel:
                puntos_actual = puntos_min
        if not puntos_siguiente:
            return 100.0
        rango = puntos_siguiente - puntos_actual
        avance = self.puntos - puntos_actual
        return round((avance / rango) * 100, 1) if rango > 0 else 100.0

    def agregar_puntos(self, cantidad, razon=''):
        self.puntos += cantidad
        # Subir de nivel
        for nivel_num, puntos_min, nombre, emoji, _ in reversed(NIVELES):
            if self.puntos >= puntos_min and nivel_num > self.nivel:
                self.nivel = nivel_num
                break
        self.save()
        return self.verificar_medallas()

    def actualizar_racha(self):
        from django.utils import timezone
        hoy = timezone.now().date()
        if self.ultimo_dia_activo:
            diferencia = (hoy - self.ultimo_dia_activo).days
            if diferencia == 1:
                self.racha_actual += 1
            elif diferencia > 1:
                self.racha_actual = 1
        else:
            self.racha_actual = 1
        if self.racha_actual > self.racha_maxima:
            self.racha_maxima = self.racha_actual
        self.ultimo_dia_activo = hoy
        self.save()

    def verificar_medallas(self):
        """Verifica y otorga medallas nuevas. Retorna lista de medallas nuevas."""
        nuevas = []
        tareas_completadas = Tarea.objects.filter(user=self.user, is_completed=True).count()
        tiempo_total = sum(t.actual_time or 0 for t in Tarea.objects.filter(user=self.user))
        amigos = Amistad.objects.filter(estado='aceptada').filter(
            solicitante=self.user) | Amistad.objects.filter(estado='aceptada').filter(receptor=self.user)
        grupos_count = Grupo.objects.filter(miembros=self.user).count()

        for config in MEDALLAS_CONFIG:
            if MedallaUsuario.objects.filter(user=self.user, codigo=config['codigo']).exists():
                continue
            otorgar = False
            tipo = config['tipo']
            cantidad = config['cantidad_requerida']
            if tipo == 'tarea' and tareas_completadas >= cantidad:
                otorgar = True
            elif tipo == 'racha' and self.racha_actual >= cantidad:
                otorgar = True
            elif tipo == 'tiempo' and tiempo_total >= cantidad:
                otorgar = True
            elif tipo == 'amigo' and amigos.count() >= cantidad:
                otorgar = True
            elif tipo == 'grupo' and grupos_count >= cantidad:
                otorgar = True
            if otorgar:
                medalla = MedallaUsuario.objects.create(
                    user=self.user,
                    codigo=config['codigo'],
                    nombre=config['nombre'],
                    emoji=config['emoji'],
                    descripcion=config['descripcion'],
                )
                nuevas.append(medalla)
        return nuevas

    def __str__(self):
        return f'{self.user.username} — Nivel {self.nivel} — {self.puntos} pts'


class MedallaUsuario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medallas')
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    emoji = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True)
    obtenida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'codigo']

    def __str__(self):
        return f'{self.emoji} {self.nombre} — {self.user.username}'


class TituloUsuario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='titulos')
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    obtenido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'codigo']

    def __str__(self):
        return f'{self.nombre} — {self.user.username}'

