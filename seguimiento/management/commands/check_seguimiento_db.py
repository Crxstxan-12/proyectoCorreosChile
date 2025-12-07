from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Verifica y corrige la tabla de eventos de seguimiento'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", ['seguimiento_eventoseguimiento'])
            ok = cursor.fetchone()
            if not ok:
                self.stderr.write('Tabla seguimiento_eventoseguimiento no existe')
                return
            cursor.execute("SHOW COLUMNS FROM seguimiento_eventoseguimiento LIKE %s", ['foto_url'])
            col = cursor.fetchone()
            if not col:
                cursor.execute("ALTER TABLE seguimiento_eventoseguimiento ADD COLUMN foto_url VARCHAR(255) NULL")
                self.stdout.write('Columna foto_url creada')
            else:
                self.stdout.write('Columna foto_url existe')
