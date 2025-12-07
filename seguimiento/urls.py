from django.urls import path
from . import views

app_name = 'seguimiento'

urlpatterns = [
    path('', views.index, name='index'),
    path('reporte/', views.reporte_pdf, name='reporte_pdf'),
    # API simple para consulta desde app móvil
    path('api/estado/<str:codigo>/', views.api_estado_envio, name='api_estado_envio'),
]
