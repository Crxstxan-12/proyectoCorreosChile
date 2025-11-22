from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db.models import Q, Count
from .models import Conductor, RutaConductor, EnvioRuta, IncidenciaConductor, MetricasConductor
from .serializers import (
    ConductorSerializer, ConductorUbicacionSerializer, ConductorEstadoSerializer,
    RutaConductorSerializer, RutaConductorCreateSerializer, EnvioRutaSerializer,
    EnvioRutaEntregaSerializer, IncidenciaConductorSerializer, MetricasConductorSerializer,
    LoginSerializer, CambiarPasswordSerializer
)
import logging

logger = logging.getLogger(__name__)


class ConductorViewSet(viewsets.ModelViewSet):
    """
    API para gestión de conductores
    """
    queryset = Conductor.objects.all()
    serializer_class = ConductorSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        """Filtrar conductores según el usuario"""
        user = self.request.user
        
        # Si es conductor, solo ver su propio perfil
        if hasattr(user, 'conductor'):
            return Conductor.objects.filter(usuario=user)
        
        # Si es administrador, ver todos
        if user.is_staff or user.is_superuser:
            return Conductor.objects.all()
        
        # Otros usuarios no ven conductores
        return Conductor.objects.none()
    
    @action(detail=True, methods=['post'])
    def actualizar_ubicacion(self, request, pk=None):
        """Actualizar ubicación del conductor"""
        conductor = self.get_object()
        serializer = ConductorUbicacionSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.update(conductor, serializer.validated_data)
            return Response({
                'status': 'success',
                'message': 'Ubicación actualizada correctamente',
                'latitud': conductor.latitud_actual,
                'longitud': conductor.longitud_actual
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado del conductor"""
        conductor = self.get_object()
        serializer = ConductorEstadoSerializer(data=request.data)
        
        if serializer.is_valid():
            estado_anterior = conductor.estado
            serializer.update(conductor, serializer.validated_data)
            return Response({
                'status': 'success',
                'message': f'Estado cambiado de {estado_anterior} a {conductor.estado}',
                'estado': conductor.estado
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """Listar conductores disponibles"""
        conductores = Conductor.objects.filter(estado='disponible', activo=True)
        serializer = self.get_serializer(conductores, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def metricas_actuales(self, request, pk=None):
        """Obtener métricas actuales del conductor"""
        conductor = self.get_object()
        hoy = timezone.now().date()
        
        try:
            metricas = MetricasConductor.objects.get(conductor=conductor, fecha=hoy)
            serializer = MetricasConductorSerializer(metricas)
            return Response(serializer.data)
        except MetricasConductor.DoesNotExist:
            return Response({
                'error': 'No hay métricas disponibles para hoy'
            }, status=status.HTTP_404_NOT_FOUND)


class RutaConductorViewSet(viewsets.ModelViewSet):
    """
    API para gestión de rutas de conductores
    """
    queryset = RutaConductor.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RutaConductorCreateSerializer
        return RutaConductorSerializer
    
    def get_queryset(self):
        """Filtrar rutas según el usuario"""
        user = self.request.user
        
        # Si es conductor, ver solo sus rutas
        if hasattr(user, 'conductor'):
            return RutaConductor.objects.filter(conductor=user.conductor)
        
        # Si es administrador, ver todas
        if user.is_staff or user.is_superuser:
            return RutaConductor.objects.all()
        
        return RutaConductor.objects.none()
    
    def get_queryset(self):
        """Filtrar rutas según el usuario y fecha"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filtrar por usuario
        if hasattr(user, 'conductor'):
            queryset = queryset.filter(conductor=user.conductor)
        
        # Filtrar por fecha si se proporciona
        fecha = self.request.query_params.get('fecha')
        if fecha:
            queryset = queryset.filter(fecha=fecha)
        
        # Filtrar por estado si se proporciona
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset.order_by('-fecha')
    
    @action(detail=True, methods=['post'])
    def iniciar_ruta(self, request, pk=None):
        """Iniciar una ruta"""
        ruta = self.get_object()
        
        if ruta.estado != 'pendiente':
            return Response({
                'error': 'La ruta ya ha sido iniciada o finalizada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ruta.estado = 'en_progreso'
        ruta.hora_inicio = timezone.now()
        ruta.save()
        
        # Cambiar estado del conductor
        ruta.conductor.cambiar_estado('en_ruta')
        
        return Response({
            'status': 'success',
            'message': 'Ruta iniciada correctamente',
            'hora_inicio': ruta.hora_inicio
        })
    
    @action(detail=True, methods=['post'])
    def finalizar_ruta(self, request, pk=None):
        """Finalizar una ruta"""
        ruta = self.get_object()
        
        if ruta.estado != 'en_progreso':
            return Response({
                'error': 'La ruta no está en progreso'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ruta.estado = 'completada'
        ruta.hora_fin = timezone.now()
        ruta.save()
        
        # Cambiar estado del conductor
        ruta.conductor.cambiar_estado('disponible')
        
        return Response({
            'status': 'success',
            'message': 'Ruta finalizada correctamente',
            'hora_fin': ruta.hora_fin,
            'progreso': ruta.progreso
        })
    
    @action(detail=True, methods=['get'])
    def envios_pendientes(self, request, pk=None):
        """Obtener envíos pendientes de la ruta"""
        ruta = self.get_object()
        envios_pendientes = ruta.envios_ruta.filter(
            estado__in=['pendiente', 'en_camino']
        ).order_by('orden_entrega')
        
        serializer = EnvioRutaSerializer(envios_pendientes, many=True)
        return Response(serializer.data)


class EnvioRutaViewSet(viewsets.ModelViewSet):
    """
    API para gestión de envíos en rutas
    """
    queryset = EnvioRuta.objects.all()
    serializer_class = EnvioRutaSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        """Filtrar envíos según el usuario"""
        user = self.request.user
        
        # Si es conductor, ver solo sus envíos
        if hasattr(user, 'conductor'):
            return EnvioRuta.objects.filter(ruta__conductor=user.conductor)
        
        # Si es administrador, ver todos
        if user.is_staff or user.is_superuser:
            return EnvioRuta.objects.all()
        
        return EnvioRuta.objects.none()
    
    @action(detail=True, methods=['post'])
    def marcar_entregado(self, request, pk=None):
        """Marcar envío como entregado"""
        envio_ruta = self.get_object()
        serializer = EnvioRutaEntregaSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                serializer.update(envio_ruta, serializer.validated_data)
                return Response({
                    'status': 'success',
                    'message': 'Envío marcado como entregado',
                    'estado': envio_ruta.estado
                })
            except Exception as e:
                logger.error(f"Error al marcar envío como entregado: {e}")
                return Response({
                    'error': 'Error al procesar la entrega'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def marcar_fallido(self, request, pk=None):
        """Marcar envío como fallido"""
        envio_ruta = self.get_object()
        serializer = EnvioRutaEntregaSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                envio_ruta.marcar_fallido(
                    motivo=serializer.validated_data.get('motivo_fallo', 'No especificado'),
                    latitud=serializer.validated_data.get('latitud'),
                    longitud=serializer.validated_data.get('longitud')
                )
                return Response({
                    'status': 'success',
                    'message': 'Envío marcado como fallido',
                    'estado': envio_ruta.estado
                })
            except Exception as e:
                logger.error(f"Error al marcar envío como fallido: {e}")
                return Response({
                    'error': 'Error al procesar el fallo'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def proximos(self, request):
        """Obtener próximos envíos a entregar"""
        user = request.user
        
        if not hasattr(user, 'conductor'):
            return Response({
                'error': 'Usuario no es conductor'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Obtener ruta actual en progreso
        try:
            ruta_actual = RutaConductor.objects.get(
                conductor=user.conductor,
                estado='en_progreso'
            )
            
            # Obtener próximos envíos pendientes
            proximos_envios = EnvioRuta.objects.filter(
                ruta=ruta_actual,
                estado__in=['pendiente', 'en_camino']
            ).order_by('orden_entrega')[:5]
            
            serializer = self.get_serializer(proximos_envios, many=True)
            return Response(serializer.data)
            
        except RutaConductor.DoesNotExist:
            return Response({
                'error': 'No hay ruta en progreso'
            }, status=status.HTTP_404_NOT_FOUND)


class IncidenciaConductorViewSet(viewsets.ModelViewSet):
    """
    API para gestión de incidencias de conductores
    """
    queryset = IncidenciaConductor.objects.all()
    serializer_class = IncidenciaConductorSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        """Filtrar incidencias según el usuario"""
        user = self.request.user
        
        # Si es conductor, ver solo sus incidencias
        if hasattr(user, 'conductor'):
            return IncidenciaConductor.objects.filter(conductor=user.conductor)
        
        # Si es administrador, ver todas
        if user.is_staff or user.is_superuser:
            return IncidenciaConductor.objects.all()
        
        return IncidenciaConductor.objects.none()
    
    def perform_create(self, serializer):
        """Asignar automáticamente el conductor al crear incidencia"""
        if hasattr(self.request.user, 'conductor'):
            serializer.save(conductor=self.request.user.conductor)
        else:
            raise serializers.ValidationError("El usuario no es un conductor")
    
    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """Resolver una incidencia"""
        incidencia = self.get_object()
        
        if incidencia.estado in ['resuelta', 'cerrada']:
            return Response({
                'error': 'La incidencia ya está resuelta o cerrada'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        incidencia.estado = 'resuelta'
        incidencia.fecha_resolucion = timezone.now()
        incidencia.save()
        
        return Response({
            'status': 'success',
            'message': 'Incidencia resuelta correctamente',
            'fecha_resolucion': incidencia.fecha_resolucion
        })


class LoginConductorAPIView(APIView):
    """
    API para login de conductores móviles
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            dispositivo_id = serializer.validated_data.get('dispositivo_id')
            token_notificacion = serializer.validated_data.get('token_notificacion')
            
            # Autenticar usuario
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Verificar si es conductor
                try:
                    conductor = user.conductor
                    
                    # Actualizar información del dispositivo
                    if dispositivo_id:
                        conductor.dispositivo_id = dispositivo_id
                    if token_notificacion:
                        conductor.token_notificacion = token_notificacion
                    conductor.save()
                    
                    # Crear o obtener token
                    token, created = Token.objects.get_or_create(user=user)
                    
                    # Serializar información del conductor
                    conductor_serializer = ConductorSerializer(conductor)
                    
                    return Response({
                        'status': 'success',
                        'message': 'Login exitoso',
                        'token': token.key,
                        'conductor': conductor_serializer.data
                    })
                    
                except Conductor.DoesNotExist:
                    return Response({
                        'error': 'El usuario no es un conductor'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutConductorAPIView(APIView):
    """
    API para logout de conductores móviles
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request):
        try:
            # Eliminar token
            request.user.auth_token.delete()
            
            # Limpiar información del dispositivo
            if hasattr(request.user, 'conductor'):
                conductor = request.user.conductor
                conductor.token_notificacion = None
                conductor.save()
            
            return Response({
                'status': 'success',
                'message': 'Logout exitoso'
            })
            
        except Exception as e:
            logger.error(f"Error en logout: {e}")
            return Response({
                'error': 'Error al procesar logout'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
