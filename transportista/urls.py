from django.urls import path
from . import views

app_name = 'transportista'

urlpatterns = [
    path('', views.index, name='index'),
    path('nuevo/', views.crear, name='crear'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/toggle/', views.toggle, name='toggle'),
]