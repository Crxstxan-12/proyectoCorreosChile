from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_web

# API Router
router = DefaultRouter()
router.register(r'tipos-vehiculo', views.TipoVehiculoViewSet)
router.register(r'vehiculos', views.VehiculoViewSet)
router.register(r'mantenimientos', views.MantenimientoVehiculoViewSet)
router.register(r'repuestos', views.RepuestoVehiculoViewSet)
router.register(r'uso-repuestos', views.UsoRepuestoMantenimientoViewSet)
router.register(r'dashboard', views.DashboardFlotaViewSet, basename='dashboard')

app_name = 'flota'

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Web URLs
    path('', views_web.dashboard_flota, name='dashboard_flota'),
    path('vehiculos/', views_web.lista_vehiculos, name='lista_vehiculos'),
    path('vehiculos/<int:vehiculo_id>/', views_web.detalle_vehiculo, name='detalle_vehiculo'),
    path('vehiculos/<int:vehiculo_id>/asignar-conductor/', views_web.asignar_conductor, name='asignar_conductor'),
    path('vehiculos/<int:vehiculo_id>/desasignar-conductor/', views_web.desasignar_conductor, name='desasignar_conductor'),
    path('vehiculos/<int:vehiculo_id>/programar-mantenimiento/', views_web.programar_mantenimiento, name='programar_mantenimiento'),
    
    path('mantenimientos/', views_web.lista_mantenimientos, name='lista_mantenimientos'),
    path('mantenimientos/<int:mantenimiento_id>/', views_web.detalle_mantenimiento, name='detalle_mantenimiento'),
    path('mantenimientos/<int:mantenimiento_id>/completar/', views_web.completar_mantenimiento, name='completar_mantenimiento'),
    
    path('repuestos/', views_web.lista_repuestos, name='lista_repuestos'),
    path('repuestos/<int:repuesto_id>/actualizar-stock/', views_web.actualizar_stock_repuesto, name='actualizar_stock_repuesto'),
]