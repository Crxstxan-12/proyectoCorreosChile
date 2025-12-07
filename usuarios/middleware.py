from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from .models import SecurityEvent


class SecurityLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            if response.status_code in (401, 403):
                user = getattr(request, 'user', None)
                SecurityEvent.objects.create(
                    usuario=None if (not user or isinstance(user, AnonymousUser) or not user.is_authenticated) else user,
                    metodo=request.method,
                    ruta=request.path,
                    ip=request.META.get('REMOTE_ADDR'),
                    status=response.status_code,
                    detalle='Acceso bloqueado por permisos',
                    ocurrido_en=timezone.now(),
                )
        except Exception:
            pass
        return response
