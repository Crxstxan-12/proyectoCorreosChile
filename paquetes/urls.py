from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TipoPaqueteViewSet, RemitenteViewSet, DestinatarioViewSet,
    PaqueteViewSet, HistorialPaqueteViewSet, RutaPaqueteViewSet,
    PuntoEntregaViewSet
)
from .views_templates import (
    DashboardPublicoView, SeguimientoClienteView, DashboardPaquetesView, 
    BuscarPaqueteView, CrearPaqueteView, APIBusquedaAjaxView, ReportePaquetesView
)

router = DefaultRouter()
router.register(r'tipos-paquete', TipoPaqueteViewSet)
router.register(r'remitentes', RemitenteViewSet)
router.register(r'destinatarios', DestinatarioViewSet)
router.register(r'paquetes', PaqueteViewSet)
router.register(r'historial', HistorialPaqueteViewSet)
router.register(r'rutas', RutaPaqueteViewSet)
router.register(r'puntos-entrega', PuntoEntregaViewSet)

app_name = 'paquetes'

urlpatterns = [
    # API REST
    path('api/', include(router.urls)),
    
    # Vistas públicas (sin login requerido)
    path('seguimiento-publico/', DashboardPublicoView.as_view(), name='dashboard_publico'),
    
    # Vistas de plantillas (requieren login)
    path('seguimiento/', SeguimientoClienteView.as_view(), name='seguimiento_cliente'),
    path('dashboard/', DashboardPaquetesView.as_view(), name='dashboard'),
    path('buscar/', BuscarPaqueteView.as_view(), name='buscar'),
    path('crear/', CrearPaqueteView.as_view(), name='crear'),
    path('reporte/', ReportePaquetesView.as_view(), name='reporte'),
    path('api/busqueda-ajax/', APIBusquedaAjaxView.as_view(), name='busqueda_ajax'),
]