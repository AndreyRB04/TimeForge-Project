from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tareas', views.TareaViewSet, basename='tarea')

urlpatterns = [
    path('', include(router.urls)),

    # Auth
    path('auth/registro/', views.registro),
    path('auth/login/', views.login),
    path('auth/logout/', views.logout),
    path('auth/perfil/', views.perfil),

    # Amigos
    path('amigos/', views.mis_amigos),
    path('amigos/solicitar/', views.enviar_solicitud),
    path('amigos/codigo/', views.agregar_por_codigo),
    path('amigos/solicitudes/', views.solicitudes_recibidas),
    path('amigos/solicitudes/<int:amistad_id>/responder/', views.responder_solicitud),

    # Grupos
    path('grupos/', views.grupos),
    path('grupos/unirse/', views.unirse_grupo),
    path('grupos/<int:grupo_id>/', views.detalle_grupo),
    path('grupos/<int:grupo_id>/invitar/', views.invitar_amigo_grupo),
    path('grupos/<int:grupo_id>/estadisticas/', views.estadisticas_grupo),

    # Tareas
    path('tareas/<int:pk>/iniciar/', views.iniciar_tarea),
    path('tareas/<int:pk>/pausar/', views.pausar_tarea),
    path('tareas/<int:pk>/terminar/', views.terminar_tarea),
]
