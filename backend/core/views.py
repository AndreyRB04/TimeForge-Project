from django.db.models import Count, Sum, Avg
from datetime import datetime, timedelta
from .models import PerfilRecompensas, MedallaUsuario, TituloUsuario, NIVELES
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
from .models import Tarea, UserToken, Amistad, Grupo, CodigoInvitacion
from .serializers import (
    TareaSerializer, UserSerializer, UserPublicoSerializer,
    AmistadSerializer, GrupoSerializer
)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_or_create_token(user):
    try:
        t = UserToken.objects.get(user=user)
        return t.key
    except UserToken.DoesNotExist:
        key = secrets.token_hex(20)
        UserToken.objects.create(user=user, key=key)
        return key


def get_user_from_request(request):
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Token '):
        key = auth.split(' ')[1]
        try:
            token = UserToken.objects.get(key=key)
            return token.user
        except UserToken.DoesNotExist:
            return None
    return None


# ── AUTH ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def registro(request):
    email = request.data.get('email', '')
    if User.objects.filter(email=email).exists():
        return Response({'error': 'El correo ya esta registrado'}, status=status.HTTP_400_BAD_REQUEST)
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token_key = get_or_create_token(user)
        return Response({
            'token': token_key,
            'user': {'id': user.id, 'username': user.username, 'email': user.email, 'first_name': user.first_name}
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    user = authenticate(username=username, password=password)
    if user:
        token_key = get_or_create_token(user)
        return Response({
            'token': token_key,
            'user': {'id': user.id, 'username': user.username, 'email': user.email, 'first_name': user.first_name}
        })
    return Response({'error': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    return Response({'message': 'Sesion cerrada'})


@api_view(['GET'])
@permission_classes([AllowAny])
def perfil(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=status.HTTP_401_UNAUTHORIZED)
    tareas = Tarea.objects.filter(user=user)
    completadas = tareas.filter(is_completed=True).count()
    tiempo_total = sum(t.actual_time or 0 for t in tareas)
    try:
        codigo = user.codigo_invitacion.codigo
    except CodigoInvitacion.DoesNotExist:
        inv = CodigoInvitacion.objects.create(user=user)
        codigo = inv.codigo
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'total_tareas': tareas.count(),
        'tareas_completadas': completadas,
        'tiempo_total_minutos': tiempo_total,
        'codigo_invitacion': codigo,
    })


# ── AMIGOS ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def enviar_solicitud(request):
    """Enviar solicitud de amistad por email"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    email = request.data.get('email', '')
    try:
        receptor = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)

    if receptor == user:
        return Response({'error': 'No puedes agregarte a ti mismo'}, status=400)

    # Verificar si ya existe amistad
    existe = Amistad.objects.filter(
        solicitante=user, receptor=receptor
    ).exists() or Amistad.objects.filter(
        solicitante=receptor, receptor=user
    ).exists()

    if existe:
        return Response({'error': 'Ya existe una solicitud o amistad con este usuario'}, status=400)

    amistad = Amistad.objects.create(solicitante=user, receptor=receptor)
    return Response(AmistadSerializer(amistad).data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def agregar_por_codigo(request):
    """Agregar amigo usando código de invitación"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    codigo = request.data.get('codigo', '')
    try:
        inv = CodigoInvitacion.objects.get(codigo=codigo)
        receptor = inv.user
    except CodigoInvitacion.DoesNotExist:
        return Response({'error': 'Código inválido'}, status=404)

    if receptor == user:
        return Response({'error': 'No puedes agregarte a ti mismo'}, status=400)

    existe = Amistad.objects.filter(
        solicitante=user, receptor=receptor
    ).exists() or Amistad.objects.filter(
        solicitante=receptor, receptor=user
    ).exists()

    if existe:
        return Response({'error': 'Ya existe una amistad con este usuario'}, status=400)

    amistad = Amistad.objects.create(solicitante=user, receptor=receptor, estado='aceptada')
    return Response(AmistadSerializer(amistad).data, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def mis_amigos(request):
    """Lista de amigos aceptados"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    amistades = Amistad.objects.filter(
        estado='aceptada'
    ).filter(
        solicitante=user
    ) | Amistad.objects.filter(
        estado='aceptada'
    ).filter(
        receptor=user
    )

    amigos = []
    for a in amistades:
        amigo = a.receptor if a.solicitante == user else a.solicitante
        amigos.append(UserPublicoSerializer(amigo).data)

    return Response(amigos)


@api_view(['GET'])
@permission_classes([AllowAny])
def solicitudes_recibidas(request):
    """Solicitudes de amistad pendientes"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    solicitudes = Amistad.objects.filter(receptor=user, estado='pendiente')
    return Response(AmistadSerializer(solicitudes, many=True).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def responder_solicitud(request, amistad_id):
    """Aceptar o rechazar solicitud"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    accion = request.data.get('accion', '')  # 'aceptar' o 'rechazar'
    try:
        amistad = Amistad.objects.get(id=amistad_id, receptor=user)
    except Amistad.DoesNotExist:
        return Response({'error': 'Solicitud no encontrada'}, status=404)

    if accion == 'aceptar':
        amistad.estado = 'aceptada'
    elif accion == 'rechazar':
        amistad.estado = 'rechazada'
    else:
        return Response({'error': 'Acción inválida'}, status=400)

    amistad.save()
    return Response(AmistadSerializer(amistad).data)


# ── GRUPOS ────────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def grupos(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    if request.method == 'GET':
        mis_grupos = Grupo.objects.filter(miembros=user)
        return Response(GrupoSerializer(mis_grupos, many=True).data)

    # POST — crear grupo
    nombre = request.data.get('nombre', '')
    descripcion = request.data.get('descripcion', '')
    if not nombre:
        return Response({'error': 'El nombre es requerido'}, status=400)

    grupo = Grupo.objects.create(creador=user, nombre=nombre, descripcion=descripcion)
    grupo.miembros.add(user)
    return Response(GrupoSerializer(grupo).data, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def detalle_grupo(request, grupo_id):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        grupo = Grupo.objects.get(id=grupo_id, miembros=user)
    except Grupo.DoesNotExist:
        return Response({'error': 'Grupo no encontrado'}, status=404)

    return Response(GrupoSerializer(grupo).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def unirse_grupo(request):
    """Unirse a un grupo con código de acceso"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    codigo = request.data.get('codigo', '')
    try:
        grupo = Grupo.objects.get(codigo_acceso=codigo)
    except Grupo.DoesNotExist:
        return Response({'error': 'Código de grupo inválido'}, status=404)

    grupo.miembros.add(user)
    return Response(GrupoSerializer(grupo).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def invitar_amigo_grupo(request, grupo_id):
    """Invitar un amigo a un grupo"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        grupo = Grupo.objects.get(id=grupo_id, miembros=user)
    except Grupo.DoesNotExist:
        return Response({'error': 'Grupo no encontrado'}, status=404)

    amigo_id = request.data.get('usuario_id')
    try:
        amigo = User.objects.get(id=amigo_id)
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)

    grupo.miembros.add(amigo)
    return Response(GrupoSerializer(grupo).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def estadisticas_grupo(request, grupo_id):
    """Estadísticas y ranking de todos los miembros del grupo"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        grupo = Grupo.objects.get(id=grupo_id, miembros=user)
    except Grupo.DoesNotExist:
        return Response({'error': 'Grupo no encontrado'}, status=404)

    estadisticas = []
    for miembro in grupo.miembros.all():
        stats = grupo.estadisticas_miembro(miembro)
        stats['usuario'] = UserPublicoSerializer(miembro).data
        estadisticas.append(stats)

    # Ordenar por tareas completadas (ranking)
    estadisticas.sort(key=lambda x: x['tareas_completadas'], reverse=True)

    # Progreso general del grupo
    total_tareas = sum(e['total_tareas'] for e in estadisticas)
    total_completadas = sum(e['tareas_completadas'] for e in estadisticas)
    progreso_general = round((total_completadas / total_tareas * 100) if total_tareas > 0 else 0, 1)

    return Response({
        'grupo': GrupoSerializer(grupo).data,
        'progreso_general': progreso_general,
        'total_tareas': total_tareas,
        'total_completadas': total_completadas,
        'ranking': estadisticas,
    })


# ── TAREAS ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def iniciar_tarea(request, pk):
    user = get_user_from_request(request)
    try:
        tarea = Tarea.objects.get(pk=pk)
        tarea.estado = 'en_progreso'
        tarea.last_start_time = timezone.now()
        tarea.save()
        return Response(TareaSerializer(tarea).data)
    except Tarea.DoesNotExist:
        return Response({'error': 'Tarea no encontrada'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def pausar_tarea(request, pk):
    try:
        tarea = Tarea.objects.get(pk=pk)
        if tarea.last_start_time and tarea.estado == 'en_progreso':
            transcurrido = int((timezone.now() - tarea.last_start_time).total_seconds()) // 60
            tarea.actual_time = (tarea.actual_time or 0) + transcurrido
        tarea.estado = 'pausada'
        tarea.last_start_time = None
        tarea.save()
        return Response(TareaSerializer(tarea).data)
    except Tarea.DoesNotExist:
        return Response({'error': 'Tarea no encontrada'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def terminar_tarea(request, pk):
    try:
        tarea = Tarea.objects.get(pk=pk)
        
        # 1. Lógica de tiempo
        if tarea.last_start_time and tarea.estado == 'en_progreso':
            transcurrido = int((timezone.now() - tarea.last_start_time).total_seconds()) // 60
            tarea.actual_time = (tarea.actual_time or 0) + transcurrido
        
        # 2. Actualización de estado
        tarea.estado = 'terminada'
        tarea.is_completed = True
        tarea.last_start_time = None
        tarea.save()
        
        # 3. Lógica de recompensas
        perfil = get_or_create_perfil(tarea.user)
        perfil.actualizar_racha()
        
        puntos = 10
        # Bonus por tiempo
        if tarea.estimated_time and tarea.actual_time:
            if tarea.actual_time <= tarea.estimated_time:
                puntos += 5
        
        nuevas_medallas = perfil.agregar_puntos(puntos, 'tarea_completada')
        
        # 4. Construcción de respuesta con recompensas
        response_data = TareaSerializer(tarea).data
        response_data['recompensa'] = {
            'puntos_ganados': puntos,
            'puntos_totales': perfil.puntos,
            'nivel': perfil.nivel,
            'nivel_nombre': perfil.nombre_nivel(),
            'nuevas_medallas': [{'nombre': m.nombre, 'emoji': m.emoji} for m in nuevas_medallas],
        }
        
        return Response(response_data)
        
    except Tarea.DoesNotExist:
        return Response({'error': 'Tarea no encontrada'}, status=404)


class TareaViewSet(viewsets.ModelViewSet):
    serializer_class = TareaSerializer

    def get_permissions(self):
        return [AllowAny()]

    def get_queryset(self):
        user = get_user_from_request(self.request)
        grupo_id = self.request.query_params.get('grupo')
        if user and grupo_id:
            return Tarea.objects.filter(user=user, grupo_id=grupo_id).order_by('-created_at')
        if user:
            return Tarea.objects.filter(user=user).order_by('-created_at')
        return Tarea.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        user = get_user_from_request(self.request)
        grupo_id = self.request.data.get('grupo')
        if user and grupo_id:
            serializer.save(user=user, grupo_id=grupo_id)
        elif user:
            serializer.save(user=user)
        else:
            serializer.save()
# ── RECOMPENSAS ───────────────────────────────────────────────────────────────

def get_or_create_perfil(user):
    perfil, _ = PerfilRecompensas.objects.get_or_create(user=user)
    return perfil


@api_view(['GET'])
@permission_classes([AllowAny])
def mi_perfil_recompensas(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    perfil = get_or_create_perfil(user)
    medallas = MedallaUsuario.objects.filter(user=user).order_by('-obtenida_en')
    titulos = TituloUsuario.objects.filter(user=user)

    # Info del nivel actual
    nivel_info = {}
    for nivel_num, puntos_min, nombre, emoji, descripcion in NIVELES:
        if nivel_num == perfil.nivel:
            nivel_info = {
                'numero': nivel_num,
                'nombre': nombre,
                'emoji': emoji,
                'descripcion': descripcion,
                'puntos_minimos': puntos_min,
            }

    return Response({
        'puntos': perfil.puntos,
        'nivel': perfil.nivel,
        'nivel_nombre': perfil.nombre_nivel(),
        'nivel_info': nivel_info,
        'progreso_nivel': perfil.progreso_nivel(),
        'puntos_siguiente_nivel': perfil.puntos_siguiente_nivel(),
        'racha_actual': perfil.racha_actual,
        'racha_maxima': perfil.racha_maxima,
        'titulo_seleccionado': perfil.titulo_seleccionado,
        'medallas': [
            {
                'codigo': m.codigo,
                'nombre': m.nombre,
                'emoji': m.emoji,
                'descripcion': m.descripcion,
                'obtenida_en': m.obtenida_en,
            } for m in medallas
        ],
        'titulos': [
            {
                'codigo': t.codigo,
                'nombre': t.nombre,
                'descripcion': t.descripcion,
            } for t in titulos
        ],
        'total_medallas': medallas.count(),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def todos_los_niveles(request):
    """Muestra el mapa de niveles completo"""
    user = get_user_from_request(request)
    perfil = get_or_create_perfil(user) if user else None

    niveles = []
    for nivel_num, puntos_min, nombre, emoji, descripcion in NIVELES:
        niveles.append({
            'numero': nivel_num,
            'nombre': f'{emoji} {nombre} Nivel {nivel_num}',
            'emoji': emoji,
            'descripcion': descripcion,
            'puntos_requeridos': puntos_min,
            'desbloqueado': perfil and perfil.nivel >= nivel_num,
        })
    return Response(niveles)


@api_view(['POST'])
@permission_classes([AllowAny])
def seleccionar_titulo(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    codigo = request.data.get('codigo', '')
    if not TituloUsuario.objects.filter(user=user, codigo=codigo).exists():
        return Response({'error': 'No tienes ese título'}, status=400)

    titulo = TituloUsuario.objects.get(user=user, codigo=codigo)
    perfil = get_or_create_perfil(user)
    perfil.titulo_seleccionado = titulo.nombre
    perfil.save()
    return Response({'titulo': titulo.nombre})


@api_view(['GET'])
@permission_classes([AllowAny])
def ranking_global(request):
    """Ranking global de todos los usuarios por puntos"""
    perfiles = PerfilRecompensas.objects.select_related('user').order_by('-puntos')[:20]
    resultado = []
    for i, p in enumerate(perfiles):
        resultado.append({
            'posicion': i + 1,
            'usuario': {
                'id': p.user.id,
                'nombre': p.user.first_name or p.user.username,
                'username': p.user.username,
            },
            'puntos': p.puntos,
            'nivel': p.nivel,
            'nivel_nombre': p.nombre_nivel(),
            'racha': p.racha_actual,
            'medallas': MedallaUsuario.objects.filter(user=p.user).count(),
        })
    return Response(resultado)

@api_view(['GET'])
@permission_classes([AllowAny])
def estadisticas_avanzadas(request):
    from django.utils import timezone
    from datetime import timedelta
    
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    periodo = request.query_params.get('periodo', 'semana')
    ahora = timezone.now()

    if periodo == 'semana':
        desde = ahora - timedelta(days=7)
    elif periodo == 'mes':
        desde = ahora - timedelta(days=30)
    elif periodo == 'trimestre':
        desde = ahora - timedelta(days=90)
    else:
        desde = ahora - timedelta(days=7)

    tareas = Tarea.objects.filter(user=user, created_at__gte=desde)
    tareas_completadas = tareas.filter(is_completed=True)

    # ── 1. Tiempo trabajado por día ──────────────────────────────────────────
    tiempo_por_dia = {}
    for i in range(7):
        dia = (ahora - timedelta(days=i)).strftime('%a')
        tiempo_por_dia[dia] = 0

    for tarea in tareas_completadas:
        dia = tarea.updated_at.strftime('%a')
        if dia in tiempo_por_dia:
            tiempo_por_dia[dia] += tarea.actual_time or 0

    dias_orden = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    dias_es = {'Mon': 'Lun', 'Tue': 'Mar', 'Wed': 'Mié', 'Thu': 'Jue', 'Fri': 'Vie', 'Sat': 'Sáb', 'Sun': 'Dom'}
    tiempo_por_dia_lista = [
        {'dia': dias_es.get(d, d), 'minutos': tiempo_por_dia.get(d, 0)}
        for d in dias_orden
    ]

    # ── 2. Tareas completadas por día (esta semana) ──────────────────────────
    tareas_por_dia = {}
    for i in range(7):
        dia = (ahora - timedelta(days=i)).strftime('%a')
        tareas_por_dia[dia] = 0

    for tarea in tareas_completadas:
        dia = tarea.updated_at.strftime('%a')
        if dia in tareas_por_dia:
            tareas_por_dia[dia] += 1

    tareas_por_dia_lista = [
        {'dia': dias_es.get(d, d), 'cantidad': tareas_por_dia.get(d, 0)}
        for d in dias_orden
    ]

    # ── 3. Horas pico (a qué hora trabajas más) ──────────────────────────────
    horas_pico = {}
    for h in range(24):
        horas_pico[h] = 0

    todas_tareas = Tarea.objects.filter(user=user, last_start_time__isnull=False)
    for tarea in todas_tareas:
        if tarea.last_start_time:
            hora = tarea.last_start_time.hour
            horas_pico[hora] += tarea.actual_time or 0

    horas_pico_lista = [
        {'hora': f'{h:02d}:00', 'minutos': horas_pico[h]}
        for h in range(24)
        if horas_pico[h] > 0
    ]
    horas_pico_lista.sort(key=lambda x: x['minutos'], reverse=True)
    top_horas = horas_pico_lista[:5]

    # Mejor hora
    mejor_hora = top_horas[0]['hora'] if top_horas else 'Sin datos'

    # ── 4. Distribución por estado ───────────────────────────────────────────
    todas = Tarea.objects.filter(user=user)
    distribucion = [
        {'estado': 'Completadas', 'cantidad': todas.filter(is_completed=True).count(), 'color': '#4CAF50'},
        {'estado': 'Pendientes', 'cantidad': todas.filter(estado='pendiente').count(), 'color': '#FF9800'},
        {'estado': 'En progreso', 'cantidad': todas.filter(estado='en_progreso').count(), 'color': '#6C63FF'},
        {'estado': 'Pausadas', 'cantidad': todas.filter(estado='pausada').count(), 'color': '#F44336'},
    ]
    distribucion = [d for d in distribucion if d['cantidad'] > 0]

    # ── 5. Eficiencia ────────────────────────────────────────────────────────
    con_tiempo = tareas_completadas.filter(
        actual_time__gt=0,
        estimated_time__gt=0
    )
    total_eficiencia = 0
    count_eficiencia = 0
    for t in con_tiempo:
        if t.estimated_time > 0:
            ef = min((t.estimated_time / t.actual_time) * 100, 100)
            total_eficiencia += ef
            count_eficiencia += 1

    eficiencia_promedio = round(total_eficiencia / count_eficiencia, 1) if count_eficiencia > 0 else 0

    # ── 6. Resumen general ───────────────────────────────────────────────────
    tiempo_total = sum(t.actual_time or 0 for t in todas)
    racha = 0
    try:
        racha = user.perfil_recompensas.racha_actual
    except:
        pass

    return Response({
        'periodo': periodo,
        'resumen': {
            'total_tareas': todas.count(),
            'completadas': todas.filter(is_completed=True).count(),
            'tiempo_total_minutos': tiempo_total,
            'eficiencia_promedio': eficiencia_promedio,
            'racha_actual': racha,
            'mejor_hora': mejor_hora,
        },
        'tiempo_por_dia': tiempo_por_dia_lista,
        'tareas_por_dia': tareas_por_dia_lista,
        'horas_pico': top_horas,
        'distribucion_estados': distribucion,
    })
