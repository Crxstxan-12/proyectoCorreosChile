from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    # Vista principal de administración
    path('', views.index, name='index'),
    
    # Configuración de plataformas
    path('configurar/', views.configurar_plataforma, name='configurar'),
    
    # Webhooks
    path('webhook/shopify/<int:plataforma_id>/', views.shopify_webhook, name='shopify_webhook'),
]