from django.contrib import admin
from .models import Perfil, SecurityEvent

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user','rol')
    list_filter = ('rol',)
    search_fields = ('user__username',)

@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ('status','metodo','ruta','usuario','ip','ocurrido_en')
    list_filter = ('status','metodo')
    search_fields = ('ruta','usuario__username','ip')
