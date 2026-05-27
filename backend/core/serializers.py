from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tarea, Amistad, Grupo, CodigoInvitacion


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
        )
        # Crear código de invitación automáticamente
        CodigoInvitacion.objects.create(user=user)
        return user


class UserPublicoSerializer(serializers.ModelSerializer):
    foto_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'email', 'foto_url']
    
    def get_foto_url(self, obj):
        try:
            return obj.perfil_usuario.foto_url
        except:
            return ''

class TareaSerializer(serializers.ModelSerializer):
    tiempo_total_actual = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_tiempo_total_actual(self, obj):
        return obj.tiempo_total_actual()


class AmistadSerializer(serializers.ModelSerializer):
    solicitante = UserPublicoSerializer(read_only=True)
    receptor = UserPublicoSerializer(read_only=True)

    class Meta:
        model = Amistad
        fields = ['id', 'solicitante', 'receptor', 'estado', 'created_at']


class GrupoSerializer(serializers.ModelSerializer):
    creador = UserPublicoSerializer(read_only=True)
    miembros = UserPublicoSerializer(many=True, read_only=True)
    total_miembros = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        fields = ['id', 'nombre','foto_url','descripcion', 'creador', 'miembros',
                  'codigo_acceso', 'total_miembros', 'created_at']
        read_only_fields = ['creador', 'codigo_acceso', 'created_at']

    def get_total_miembros(self, obj):
        return obj.miembros.count()


class EstadisticasMiembroSerializer(serializers.Serializer):
    usuario = UserPublicoSerializer()
    total_tareas = serializers.IntegerField()
    tareas_completadas = serializers.IntegerField()
    tiempo_trabajado = serializers.IntegerField()
    progreso = serializers.FloatField()
