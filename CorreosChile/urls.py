"""
URL configuration for CorreosChile project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', lambda request: redirect('paquetes:dashboard_publico'), name='home'),
    path('admin/', admin.site.urls),
    path('envios/', include('envios.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('reclamos/', include('reclamos.urls')),
    path('seguimiento/', include('seguimiento.urls')),
    path('transportistas/', include('transportista.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('ecommerce/', include('ecommerce.urls')),
    path('cliente/', include('clientes.urls')),
    path('conductores/', include('conductores.urls')),
    path('flota/', include('flota.urls')),
    path('paquetes/', include('paquetes.urls')),
]

# Configuración para servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
