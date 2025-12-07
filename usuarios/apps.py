from django.apps import AppConfig
from django.db import connection


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        try:
            with connection.cursor() as c:
                # Asegurar columnas de bloqueo de login
                c.execute("SHOW TABLES LIKE %s", ['usuarios_perfil'])
                if not c.fetchone():
                    return
                c.execute("SHOW COLUMNS FROM usuarios_perfil LIKE %s", ['intentos_fallidos'])
                if not c.fetchone():
                    c.execute("ALTER TABLE usuarios_perfil ADD COLUMN intentos_fallidos INT UNSIGNED NOT NULL DEFAULT 0")
                c.execute("SHOW COLUMNS FROM usuarios_perfil LIKE %s", ['bloqueado_hasta'])
                if not c.fetchone():
                    c.execute("ALTER TABLE usuarios_perfil ADD COLUMN bloqueado_hasta DATETIME NULL")
        except Exception:
            # No bloquear el arranque si falla la verificación
            pass
