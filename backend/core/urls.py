from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tareas', views.TareaViewSet, basename='tarea')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/registro/', views.registro),
    path('auth/login/', views.login),
    path('auth/logout/', views.logout),
    path('auth/perfil/', views.perfil),
    path('tareas/<int:pk>/iniciar/', views.iniciar_tarea),
    path('tareas/<int:pk>/pausar/', views.pausar_tarea),
    path('tareas/<int:pk>/terminar/', views.terminar_tarea),
]