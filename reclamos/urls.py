from django.urls import path
from . import views

app_name = 'reclamos'

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('reporte/', views.reporte_pdf, name='reporte_pdf'),
    path('nuevo/', views.nuevo, name='nuevo'),
    path('mis/', views.mis, name='mis'),
]
