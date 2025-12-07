from django.apps import AppConfig


class EcommerceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ecommerce'
    verbose_name = 'Integración E-commerce'

    def ready(self):
        try:
            from . import signals  # noqa
        except Exception:
            pass
