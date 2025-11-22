from django.apps import AppConfig


class NotificacionesMejoradasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificaciones_mejoradas'
    verbose_name = 'Sistema de Notificaciones Mejorado'

    def ready(self):
        # Importar señales cuando la app esté lista
        import notificaciones_mejoradas.signals
