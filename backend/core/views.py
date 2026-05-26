from django.db.models import Count, Sum, Avg
from django.core.mail import send_mail
from django.conf import settings
from .models import PerfilUsuario, CodigoRecuperacion
from .models import Competencia, ParticipanteCompetencia, RetoCompetencia
from datetime import timedelta
from .firebase_service import enviar_notificacion
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

    existe = Amistad.objects.filter(
        solicitante=user, receptor=receptor
    ).exists() or Amistad.objects.filter(
        solicitante=receptor, receptor=user
    ).exists()

    if existe:
        return Response({'error': 'Ya existe una solicitud o amistad con este usuario'}, status=400)

    amistad = Amistad.objects.create(solicitante=user, receptor=receptor)
    # NOTIFICACIÓN AGREGADA:
    notif_solicitud_amistad(receptor, user) 
    
    return Response(AmistadSerializer(amistad).data, status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
def responder_solicitud(request, amistad_id):
    """Aceptar o rechazar solicitud"""
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    accion = request.data.get('accion', '')
    try:
        amistad = Amistad.objects.get(id=amistad_id, receptor=user)
    except Amistad.DoesNotExist:
        return Response({'error': 'Solicitud no encontrada'}, status=404)

    if accion == 'aceptar':
        amistad.estado = 'aceptada'
        # NOTIFICACIÓN AGREGADA:
        notif_solicitud_aceptada(amistad.solicitante, user)
    elif accion == 'rechazar':
        amistad.estado = 'rechazada'
    else:
        return Response({'error': 'Acción inválida'}, status=400)

    amistad.save()
    return Response(AmistadSerializer(amistad).data)


# ── GRUPOS ────────────────────────────────────────────────────────────────────

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
    # NOTIFICACIÓN AGREGADA:
    notif_nuevo_miembro_grupo(grupo, user)
    
    return Response(GrupoSerializer(grupo).data)


# ── TAREAS ────────────────────────────────────────────────────────────────────

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
        nivel_anterior = perfil.nivel
        racha_anterior = perfil.racha_actual
        perfil.actualizar_racha()
        perfil.save()  # Garantizar que la racha se persiste en BD
        
        puntos = 10
        if tarea.estimated_time and tarea.actual_time:
            if tarea.actual_time <= tarea.estimated_time:
                puntos += 5
        
        nuevas_medallas = perfil.agregar_puntos(puntos, 'tarea_completada')

        # NOTIFICACIONES AGREGADAS:
        for medalla in nuevas_medallas:
            notif_nueva_medalla(tarea.user, medalla.nombre, medalla.emoji)

        if perfil.nivel > nivel_anterior:
            notif_subida_nivel(tarea.user, perfil.nombre_nivel())
        
        # 4. Construcción de respuesta
        response_data = TareaSerializer(tarea).data
        response_data['recompensa'] = {
            'puntos_ganados': puntos,
            'puntos_totales': perfil.puntos,
            'nivel': perfil.nivel,
            'nivel_nombre': perfil.nombre_nivel(),
            'nuevas_medallas': [{'nombre': m.nombre, 'emoji': m.emoji} for m in nuevas_medallas],
            'racha_actual': perfil.racha_actual,
            'racha_maxima': perfil.racha_maxima,
            'racha_subio': perfil.racha_actual > racha_anterior,
        }
        
        return Response(response_data)
        
    except Tarea.DoesNotExist:
        return Response({'error': 'Tarea no encontrada'}, status=404)
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
        'ultimo_dia_activo': str(perfil.ultimo_dia_activo),
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

@api_view(['POST'])
@permission_classes([AllowAny])
def guardar_fcm_token(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)
    token = request.data.get('fcm_token', '')
    if token:
        from .models import FCMToken
        FCMToken.objects.update_or_create(user=user, defaults={'token': token})
    return Response({'ok': True})


# ── FUNCIONES HELPER PARA ENVIAR NOTIFICACIONES ───────────────────────────────
# Llama estas funciones desde donde necesites en views.py

def _get_fcm_token(user):
    """Obtiene el FCM token del usuario de forma segura."""
    try:
        from .models import FCMToken
        fcm = FCMToken.objects.get(user=user)
        return fcm.token
    except Exception:
        return None


def notif_solicitud_amistad(receptor, solicitante):
    token = _get_fcm_token(receptor)
    if not token:
        return
    try:
        enviar_notificacion(
            token,
            '👋 Nueva solicitud de amistad',
            f'{solicitante.first_name or solicitante.username} quiere ser tu amigo',
            {'tipo': 'solicitud_amistad'}
        )
    except Exception:
        pass

def notif_solicitud_aceptada(solicitante, receptor):
    token = _get_fcm_token(solicitante)
    if not token:
        return
    try:
        enviar_notificacion(
            token,
            '✅ Solicitud aceptada',
            f'{receptor.first_name or receptor.username} aceptó tu solicitud',
            {'tipo': 'solicitud_aceptada'}
        )
    except Exception:
        pass

def notif_nuevo_miembro_grupo(grupo, nuevo_miembro):
    try:
        for miembro in grupo.miembros.exclude(id=nuevo_miembro.id):
            token = _get_fcm_token(miembro)
            if not token:
                continue
            try:
                enviar_notificacion(
                    token,
                    '👥 Nuevo miembro en tu grupo',
                    f'{nuevo_miembro.first_name or nuevo_miembro.username} se unió a {grupo.nombre}',
                    {'tipo': 'nuevo_miembro', 'grupo_id': str(grupo.id)}
                )
            except Exception:
                pass
    except Exception:
        pass

def notif_subida_nivel(user, nivel_nombre):
    token = _get_fcm_token(user)
    if not token:
        return
    try:
        enviar_notificacion(
            token,
            '🎉 ¡Subiste de nivel!',
            f'Ahora eres {nivel_nombre} — ¡sigue así!',
            {'tipo': 'subida_nivel'}
        )
    except Exception:
        pass

def notif_nueva_medalla(user, nombre_medalla, emoji):
    token = _get_fcm_token(user)
    if not token:
        return
    try:
        enviar_notificacion(
            token,
            f'{emoji} ¡Nueva medalla!',
            f'Obtuviste: {nombre_medalla}',
            {'tipo': 'nueva_medalla'}
        )
    except Exception:
        pass
# ── AGREGAR ESTAS FUNCIONES AL FINAL DE views.py ─────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def agregar_por_codigo(request):
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
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)
    amistades = Amistad.objects.filter(
        estado='aceptada'
    ).filter(solicitante=user) | Amistad.objects.filter(
        estado='aceptada'
    ).filter(receptor=user)
    amigos = []
    for a in amistades:
        amigo = a.receptor if a.solicitante == user else a.solicitante
        amigos.append(UserPublicoSerializer(amigo).data)
    return Response(amigos)


@api_view(['GET'])
@permission_classes([AllowAny])
def solicitudes_recibidas(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)
    solicitudes = Amistad.objects.filter(receptor=user, estado='pendiente')
    return Response(AmistadSerializer(solicitudes, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def grupos(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)
    if request.method == 'GET':
        mis_grupos = Grupo.objects.filter(miembros=user)
        return Response(GrupoSerializer(mis_grupos, many=True).data)
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
def invitar_amigo_grupo(request, grupo_id):
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
    estadisticas.sort(key=lambda x: x['tareas_completadas'], reverse=True)
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
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def competencias_grupo(request, grupo_id):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        grupo = Grupo.objects.get(id=grupo_id, miembros=user)
    except Grupo.DoesNotExist:
        return Response({'error': 'Grupo no encontrado'}, status=404)

    if request.method == 'GET':
        competencias = Competencia.objects.filter(grupo=grupo).order_by('-created_at')
        resultado = []
        for c in competencias:
            participando = ParticipanteCompetencia.objects.filter(
                competencia=c, user=user
            ).exists()
            resultado.append({
                'id': c.id,
                'nombre': c.nombre,
                'descripcion': c.descripcion,
                'fecha_inicio': c.fecha_inicio,
                'fecha_fin': c.fecha_fin,
                'estado': c.estado,
                'dias_restantes': c.dias_restantes(),
                'esta_activa': c.esta_activa(),
                'total_participantes': c.participantes.count(),
                'participando': participando,
                'creador': c.creador.first_name or c.creador.username,
            })
        return Response(resultado)

    # POST — crear competencia mensual
    # Evitar duplicados: si ya hay una competencia activa este mes, rechazar
    ahora_check = timezone.now()
    mes_inicio_check = ahora_check.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if ahora_check.month == 12:
        mes_fin_check = ahora_check.replace(year=ahora_check.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        mes_fin_check = ahora_check.replace(month=ahora_check.month + 1, day=1) - timedelta(seconds=1)

    competencia_existente = Competencia.objects.filter(
        grupo=grupo,
        fecha_inicio__gte=mes_inicio_check,
        fecha_fin__lte=mes_fin_check,
    ).first()
    if competencia_existente:
        return Response({
            'error': 'Ya existe una competencia activa este mes para este grupo',
            'competencia_id': competencia_existente.id,
        }, status=400)

    nombre = request.data.get('nombre', f'Competencia de {timezone.now().strftime("%B %Y")}')
    descripcion = request.data.get('descripcion', '')

    ahora = timezone.now()
    # Inicio: primer día del mes actual
    inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Fin: último día del mes
    if ahora.month == 12:
        fin = ahora.replace(year=ahora.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        fin = ahora.replace(month=ahora.month + 1, day=1) - timedelta(seconds=1)

    competencia = Competencia.objects.create(
        grupo=grupo,
        nombre=nombre,
        descripcion=descripcion,
        fecha_inicio=inicio,
        fecha_fin=fin,
        creador=user,
    )

    # Agregar al creador como participante
    ParticipanteCompetencia.objects.create(competencia=competencia, user=user)

    # Crear retos automáticos
    retos_default = [
        {'titulo': 'Primer paso', 'descripcion': 'Completa 5 tareas este mes', 'tipo': 'tareas', 'meta': 5, 'emoji': '🎯', 'puntos_bonus': 30},
        {'titulo': 'Dedicado', 'descripcion': 'Trabaja 10 horas este mes', 'tipo': 'tiempo', 'meta': 10, 'emoji': '⏱️', 'puntos_bonus': 50},
        {'titulo': 'Constante', 'descripcion': 'Mantén una racha de 7 días', 'tipo': 'racha', 'meta': 7, 'emoji': '🔥', 'puntos_bonus': 70},
        {'titulo': 'Productivo', 'descripcion': 'Acumula 500 puntos', 'tipo': 'puntos', 'meta': 500, 'emoji': '⭐', 'puntos_bonus': 100},
        {'titulo': 'Campeón', 'descripcion': 'Completa 20 tareas este mes', 'tipo': 'tareas', 'meta': 20, 'emoji': '🏆', 'puntos_bonus': 150},
    ]

    for r in retos_default:
        RetoCompetencia.objects.create(competencia=competencia, **r)

    return Response({
        'id': competencia.id,
        'nombre': competencia.nombre,
        'fecha_inicio': competencia.fecha_inicio,
        'fecha_fin': competencia.fecha_fin,
        'dias_restantes': competencia.dias_restantes(),
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def unirse_competencia(request, competencia_id):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        competencia = Competencia.objects.get(id=competencia_id)
        # Verificar que el user es miembro del grupo
        if not competencia.grupo.miembros.filter(id=user.id).exists():
            return Response({'error': 'No eres miembro de este grupo'}, status=403)
    except Competencia.DoesNotExist:
        return Response({'error': 'Competencia no encontrada'}, status=404)

    ParticipanteCompetencia.objects.get_or_create(competencia=competencia, user=user)
    return Response({'ok': True, 'mensaje': '¡Te uniste a la competencia!'})


@api_view(['GET'])
@permission_classes([AllowAny])
def ranking_competencia(request, competencia_id):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        competencia = Competencia.objects.get(id=competencia_id)
    except Competencia.DoesNotExist:
        return Response({'error': 'Competencia no encontrada'}, status=404)

    ranking_data = competencia.get_ranking()
    resultado = []
    for i, r in enumerate(ranking_data):
        u = r['usuario']
        resultado.append({
            'posicion': i + 1,
            'usuario': {
                'id': u.id,
                'nombre': u.first_name or u.username,
                'username': u.username,
            },
            'tareas_completadas': r['tareas_completadas'],
            'tiempo_trabajado': r['tiempo_trabajado'],
            'puntos_recompensas': r['puntos_recompensas'],
            'racha': r['racha'],
            'score_total': r['score_total'],
            'es_yo': u.id == user.id,
        })

    return Response({
        'competencia': {
            'id': competencia.id,
            'nombre': competencia.nombre,
            'dias_restantes': competencia.dias_restantes(),
            'esta_activa': competencia.esta_activa(),
            'fecha_fin': competencia.fecha_fin,
        },
        'ranking': resultado,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def retos_competencia(request, competencia_id):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    try:
        competencia = Competencia.objects.get(id=competencia_id)
    except Competencia.DoesNotExist:
        return Response({'error': 'Competencia no encontrada'}, status=404)

    retos = RetoCompetencia.objects.filter(competencia=competencia)
    resultado = []
    for r in retos:
        progreso = r.progreso_usuario(user, competencia)
        completado = progreso >= r.meta
        pct = min(round((progreso / r.meta) * 100), 100) if r.meta > 0 else 0
        resultado.append({
            'id': r.id,
            'titulo': r.titulo,
            'descripcion': r.descripcion,
            'tipo': r.tipo,
            'meta': r.meta,
            'progreso': progreso,
            'porcentaje': pct,
            'completado': completado,
            'emoji': r.emoji,
            'puntos_bonus': r.puntos_bonus,
        })

    return Response(resultado)

# ── PERFIL PERSONALIZABLE ─────────────────────────────────────────────────────

@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def perfil_personalizado(request):
    user = get_user_from_request(request)
    if not user:
        return Response({'error': 'No autorizado'}, status=401)

    perfil, _ = PerfilUsuario.objects.get_or_create(user=user)

    if request.method == 'GET':
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'foto_url': perfil.foto_url,
            'biografia': perfil.biografia,
            'carrera': perfil.carrera,
            'meta_diaria': perfil.meta_diaria,
        })

    # PUT — actualizar perfil
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.save()

    perfil.biografia = request.data.get('biografia', perfil.biografia)
    perfil.carrera = request.data.get('carrera', perfil.carrera)
    perfil.meta_diaria = request.data.get('meta_diaria', perfil.meta_diaria)

    # Foto de perfil (base64)
    foto = request.data.get('foto_url', '')
    if foto:
        perfil.foto_url = foto

    perfil.save()

    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'foto_url': perfil.foto_url,
        'biografia': perfil.biografia,
        'carrera': perfil.carrera,
        'meta_diaria': perfil.meta_diaria,
    })


# ── RECUPERAR CONTRASEÑA ──────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_codigo_recuperacion(request):
    """Paso 1: Enviar código de 6 dígitos al email"""
    email = request.data.get('email', '').strip()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Por seguridad, no revelar si el email existe
        return Response({'mensaje': 'Si el correo existe, recibirás un código'})

    # Generar código
    codigo = CodigoRecuperacion.generar_codigo()
    CodigoRecuperacion.objects.create(
        user=user,
        email=email,
        codigo=codigo,
    )

    # Enviar email
    try:
        send_mail(
            subject='🔐 Código de recuperación — TimeForge',
            message=f'''
Hola {user.first_name or user.username},

Tu código de recuperación de contraseña es:

        {codigo}

Este código es válido por 15 minutos.

Si no solicitaste este código, ignora este mensaje.

— El equipo de TimeForge
            ''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        print(f'Error enviando email: {e}')
        return Response({'error': 'Error al enviar el correo'}, status=500)

    return Response({'mensaje': 'Código enviado a tu correo'})


@api_view(['POST'])
@permission_classes([AllowAny])
def verificar_codigo_recuperacion(request):
    """Paso 2: Verificar código"""
    email = request.data.get('email', '').strip()
    codigo = request.data.get('codigo', '').strip()

    try:
        registro = CodigoRecuperacion.objects.filter(
            email=email,
            codigo=codigo,
            usado=False,
        ).latest('created_at')
    except CodigoRecuperacion.DoesNotExist:
        return Response({'error': 'Código inválido o expirado'}, status=400)

    if not registro.esta_vigente():
        return Response({'error': 'El código ha expirado'}, status=400)

    return Response({'valido': True, 'email': email})


@api_view(['POST'])
@permission_classes([AllowAny])
def cambiar_contrasena(request):
    """Paso 3: Cambiar contraseña con código verificado"""
    email = request.data.get('email', '').strip()
    codigo = request.data.get('codigo', '').strip()
    nueva_password = request.data.get('nueva_password', '').strip()

    if len(nueva_password) < 6:
        return Response({'error': 'La contraseña debe tener al menos 6 caracteres'}, status=400)

    try:
        registro = CodigoRecuperacion.objects.filter(
            email=email,
            codigo=codigo,
            usado=False,
        ).latest('created_at')
    except CodigoRecuperacion.DoesNotExist:
        return Response({'error': 'Código inválido'}, status=400)

    if not registro.esta_vigente():
        return Response({'error': 'El código ha expirado'}, status=400)

    # Cambiar contraseña
    user = registro.user
    user.set_password(nueva_password)
    user.save()

    # Marcar código como usado
    registro.usado = True
    registro.save()

    return Response({'mensaje': '¡Contraseña actualizada exitosamente!'})


# ── LOGIN CON GOOGLE ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def login_google(request):
    """Recibe el token de Google y autentica al usuario"""
    import requests as req

    google_token = request.data.get('google_token', '')
    if not google_token:
        return Response({'error': 'Token de Google requerido'}, status=400)

    # Verificar token con Google
    try:
        google_response = req.get(
            f'https://oauth2.googleapis.com/tokeninfo?id_token={google_token}'
        )
        google_data = google_response.json()

        if 'error' in google_data:
            return Response({'error': 'Token de Google inválido'}, status=400)

        email = google_data.get('email', '')
        nombre = google_data.get('given_name', '')
        apellido = google_data.get('family_name', '')
        foto = google_data.get('picture', '')

        if not email:
            return Response({'error': 'No se pudo obtener el email de Google'}, status=400)

        # Crear o recuperar usuario
        user, creado = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'first_name': nombre,
                'last_name': apellido,
            }
        )

        if creado:
            user.set_unusable_password()
            user.save()
            # Crear código de invitación
            CodigoInvitacion.objects.get_or_create(user=user)
            # Crear perfil con foto de Google
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil.foto_url = foto
            perfil.save()

        token_key = get_or_create_token(user)
        return Response({
            'token': token_key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'nuevo_usuario': creado,
        })

    except Exception as e:
        return Response({'error': f'Error al verificar con Google: {str(e)}'}, status=500)
