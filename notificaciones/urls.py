from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.index, name='index'),
    path('reporte/', views.reporte_pdf, name='reporte_pdf'),
]