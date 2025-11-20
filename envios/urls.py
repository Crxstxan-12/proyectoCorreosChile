from django.urls import path
from . import views

app_name = 'envios'

urlpatterns = [
    path('', views.index, name='index'),
    path('scan/', views.scan_bultos, name='scan_bultos'),
    path('reporte/', views.reporte_pdf, name='reporte_pdf'),
]