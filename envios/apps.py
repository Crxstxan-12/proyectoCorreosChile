from django.apps import AppConfig
from django.db import connection


class EnviosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'envios'

    def ready(self):
        try:
            with connection.cursor() as c:
                c.execute("SHOW TABLES LIKE %s", ['envios_envio'])
                if not c.fetchone():
                    return
                for col_sql in [
                    ("fecha_estimada_entrega", "ALTER TABLE envios_envio ADD COLUMN fecha_estimada_entrega DATETIME NULL"),
                    ("eta_actualizado_en", "ALTER TABLE envios_envio ADD COLUMN eta_actualizado_en DATETIME NULL"),
                    ("eta_km_restante", "ALTER TABLE envios_envio ADD COLUMN eta_km_restante DECIMAL(7,2) NULL"),
                    ("destino_lat", "ALTER TABLE envios_envio ADD COLUMN destino_lat DECIMAL(9,6) NULL"),
                    ("destino_lng", "ALTER TABLE envios_envio ADD COLUMN destino_lng DECIMAL(9,6) NULL"),
                ]:
                    c.execute("SHOW COLUMNS FROM envios_envio LIKE %s", [col_sql[0]])
                    if not c.fetchone():
                        c.execute(col_sql[1])
        except Exception:
            pass
