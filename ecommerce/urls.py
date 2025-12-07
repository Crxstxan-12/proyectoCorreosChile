from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    # Vista principal de administración
    path('', views.index, name='index'),
    
    # Configuración de plataformas
    path('configurar/', views.configurar_plataforma, name='configurar'),
    
    # Acciones de pedidos
    path('procesar/<int:pedido_id>/', views.procesar_pedido, name='procesar'),
    path('asignar_transportista/<int:pedido_id>/', views.asignar_transportista, name='asignar_transportista'),
    # Pedidos directos por usuarios
    path('nuevo/', views.nuevo_pedido, name='nuevo_pedido'),
    path('mis/', views.mis_pedidos, name='mis_pedidos'),
    path('tienda/', views.tienda, name='tienda'),
    path('reenviar_estado/<int:pedido_id>/', views.reenviar_estado, name='reenviar_estado'),
    path('sandbox/status', views.sandbox_status, name='sandbox_status'),
    path('probar_sync/<int:pedido_id>/', views.probar_sync, name='probar_sync'),
    
    # Webhooks
    path('webhook/shopify/<int:plataforma_id>/', views.shopify_webhook, name='shopify_webhook'),
    path('webhook/amazon/<int:plataforma_id>/', views.amazon_webhook, name='amazon_webhook'),
]
