from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
import secrets
from .models import Tarea, UserToken
from .serializers import TareaSerializer, UserSerializer


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


@api_view(['POST'])
@permission_classes([AllowAny])
def registro(request):
    email = request.data.get('email', '')
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'El correo ya esta registrado'},
            status=status.HTTP_400_BAD_REQUEST
        )
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token_key = get_or_create_token(user)
        return Response({
            'token': token_key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
            }
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
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
            }
        })
    return Response(
        {'error': 'Credenciales incorrectas'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    return Response({'message': 'Sesion cerrada'})


@api_view(['GET'])
@permission_classes([AllowAny])
def perfil(request):
    user = get_user_from_request(request)
    if not user:
        return Response(
            {'error': 'No autorizado'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    tareas = Tarea.objects.filter(user=user)
    completadas = tareas.filter(is_completed=True).count()
    tiempo_total = sum(t.actual_time or 0 for t in tareas)
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'total_tareas': tareas.count(),
        'tareas_completadas': completadas,
        'tiempo_total_minutos': tiempo_total,
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
            # CORRECCIÓN: usar total_seconds() en lugar de .seconds
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
        if tarea.last_start_time and tarea.estado == 'en_progreso':
            # CORRECCIÓN: usar total_seconds() en lugar de .seconds
            transcurrido = int((timezone.now() - tarea.last_start_time).total_seconds()) // 60
            tarea.actual_time = (tarea.actual_time or 0) + transcurrido
        tarea.estado = 'terminada'
        tarea.is_completed = True
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
        if user:
            return Tarea.objects.filter(user=user).order_by('-created_at')
        return Tarea.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        user = get_user_from_request(self.request)
        if user:
            serializer.save(user=user)
        else:
            serializer.save()