from django.apps import AppConfig


class PaquetesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'paquetes'
    
    def ready(self):
        import paquetes.signals
