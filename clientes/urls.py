from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_cliente, name='dashboard_cliente'),
    
    # Gestión de envíos
    path('mis-envios/', views.mis_envios, name='mis_envios'),
    path('envio/<str:codigo>/', views.detalle_envio, name='detalle_envio'),
    
    # Perfil y configuración
    path('perfil/', views.perfil_cliente, name='perfil_cliente'),
    path('preferencias-notificaciones/', views.preferencias_notificaciones, name='preferencias_notificaciones'),
    path('notificaciones/', views.notificaciones_cliente, name='notificaciones_cliente'),
    
    # Direcciones de entrega
    path('agregar-direccion/', views.agregar_direccion, name='agregar_direccion'),
    
    # Reportes
    path('descargar-reporte/', views.descargar_reporte, name='descargar_reporte'),
]