from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    ConductorViewSet,
    RutaConductorViewSet,
    EnvioRutaViewSet,
    IncidenciaConductorViewSet,
    LoginConductorAPIView,
    LogoutConductorAPIView,
)
from .views_web import (
    dashboard_conductor,
    mis_rutas,
    detalle_ruta,
    mis_incidencias,
    crear_incidencia,
    mi_perfil_conductor,
    actualizar_estado,
    actualizar_ubicacion,
)

app_name = 'conductores'

# Crear router para las viewsets
router = DefaultRouter()
router.register(r'conductores', ConductorViewSet)
router.register(r'rutas', RutaConductorViewSet)
router.register(r'envios-ruta', EnvioRutaViewSet)
router.register(r'incidencias', IncidenciaConductorViewSet)

urlpatterns = [
    # Rutas web del dashboard de conductores
    path('', dashboard_conductor, name='dashboard'),
    path('mis-rutas/', mis_rutas, name='mis_rutas'),
    path('ruta/<int:ruta_id>/', detalle_ruta, name='detalle_ruta'),
    path('mis-incidencias/', mis_incidencias, name='mis_incidencias'),
    path('crear-incidencia/', crear_incidencia, name='crear_incidencia'),
    path('mi-perfil/', mi_perfil_conductor, name='mi_perfil'),
    
    # APIs AJAX
    path('api/actualizar-estado/', actualizar_estado, name='actualizar_estado'),
    path('api/actualizar-ubicacion/', actualizar_ubicacion, name='actualizar_ubicacion'),
    
    # Rutas del router API
    path('api/', include(router.urls)),
    
    # Autenticación API
    path('api/login/', LoginConductorAPIView.as_view(), name='login_conductor'),
    path('api/logout/', LogoutConductorAPIView.as_view(), name='logout_conductor'),
    path('api/token-auth/', obtain_auth_token, name='api_token_auth'),
]