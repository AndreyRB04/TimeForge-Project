from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tarea

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
        return user


class TareaSerializer(serializers.ModelSerializer):
    tiempo_total_actual = serializers.SerializerMethodField()

    class Meta:
        model = Tarea
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_tiempo_total_actual(self, obj):
        return obj.tiempo_total_actual()