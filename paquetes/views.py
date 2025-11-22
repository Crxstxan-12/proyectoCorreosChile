from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Count
from .models import TipoPaquete, Remitente, Destinatario, Paquete, HistorialPaquete, RutaPaquete, PuntoEntrega
from .serializers import (
    TipoPaqueteSerializer, RemitenteSerializer, DestinatarioSerializer,
    PaqueteListSerializer, PaqueteDetailSerializer, PaqueteCreateSerializer,
    SeguimientoPaqueteSerializer, ActualizarEstadoSerializer,
    GenerarEtiquetaSerializer, RutaPaqueteSerializer, PuntoEntregaSerializer,
    HistorialPaqueteSerializer
)


class TipoPaqueteViewSet(viewsets.ModelViewSet):
    queryset = TipoPaquete.objects.filter(activo=True)
    serializer_class = TipoPaqueteSerializer
    permission_classes = [IsAuthenticated]


class RemitenteViewSet(viewsets.ModelViewSet):
    queryset = Remitente.objects.all()
    serializer_class = RemitenteSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nombre_completo', 'numero_documento', 'email', 'telefono']


class DestinatarioViewSet(viewsets.ModelViewSet):
    queryset = Destinatario.objects.all()
    serializer_class = DestinatarioSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nombre_completo', 'email', 'telefono']


class PuntoEntregaViewSet(viewsets.ModelViewSet):
    queryset = PuntoEntrega.objects.filter(activo=True)
    serializer_class = PuntoEntregaSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nombre', 'direccion', 'comuna']


class PaqueteViewSet(viewsets.ModelViewSet):
    queryset = Paquete.objects.all().select_related(
        'remitente', 'destinatario', 'tipo_paquete'
    ).prefetch_related('historial', 'rutas')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PaqueteListSerializer
        elif self.action == 'create':
            return PaqueteCreateSerializer
        elif self.action == 'seguimiento':
            return SeguimientoPaqueteSerializer
        elif self.action == 'generar_etiqueta':
            return GenerarEtiquetaSerializer
        return PaqueteDetailSerializer
    
    def get_permissions(self):
        if self.action == 'seguimiento':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros de búsqueda
        codigo_seguimiento = self.request.query_params.get('codigo_seguimiento')
        estado = self.request.query_params.get('estado')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        remitente = self.request.query_params.get('remitente')
        destinatario = self.request.query_params.get('destinatario')
        
        if codigo_seguimiento:
            queryset = queryset.filter(codigo_seguimiento__icontains=codigo_seguimiento)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_creacion__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_creacion__lte=fecha_fin)
        if remitente:
            queryset = queryset.filter(remitente__nombre_completo__icontains=remitente)
        if destinatario:
            queryset = queryset.filter(destinatario__nombre_completo__icontains=destinatario)
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paquete = serializer.save()
        
        # Crear el primer registro en el historial
        HistorialPaquete.objects.create(
            paquete=paquete,
            estado_anterior='registrado',
            estado_nuevo='registrado',
            observacion='Paquete registrado en el sistema'
        )
        
        # Retornar el paquete con el serializador de detalle
        detail_serializer = PaqueteDetailSerializer(paquete)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def actualizar_estado(self, request, pk=None):
        paquete = self.get_object()
        serializer = ActualizarEstadoSerializer(
            data=request.data, 
            context={'paquete': paquete}
        )
        serializer.is_valid(raise_exception=True)
        
        nuevo_estado = serializer.validated_data['nuevo_estado']
        ubicacion = serializer.validated_data.get('ubicacion', '')
        observaciones = serializer.validated_data.get('observaciones', '')
        
        # Actualizar el estado del paquete
        estado_anterior = paquete.estado
        paquete.estado = nuevo_estado
        paquete.save()
        
        # Registrar en el historial
        HistorialPaquete.objects.create(
            paquete=paquete,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            ubicacion=ubicacion,
            observacion=observaciones
        )
        
        # Si el estado es "entregado", actualizar la ruta correspondiente
        if nuevo_estado == 'entregado':
            RutaPaquete.objects.filter(
                paquete=paquete,
                completado=False
            ).update(completado=True, fecha_llegada=timezone.now())
        
        return Response({
            'mensaje': 'Estado actualizado exitosamente',
            'paquete': PaqueteDetailSerializer(paquete).data
        })
    
    @action(detail=False, methods=['get'])
    def seguimiento(self, request):
        codigo_seguimiento = request.query_params.get('codigo_seguimiento')
        
        if not codigo_seguimiento:
            return Response(
                {'error': 'Se requiere el código de seguimiento'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paquete = get_object_or_404(Paquete, codigo_seguimiento=codigo_seguimiento)
        serializer = SeguimientoPaqueteSerializer(paquete)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def generar_etiqueta(self, request, pk=None):
        paquete = self.get_object()
        serializer = GenerarEtiquetaSerializer(paquete)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        # Estadísticas generales de paquetes
        total = Paquete.objects.count()
        por_estado = Paquete.objects.values('estado').annotate(
            cantidad=Count('id')
        ).order_by('-cantidad')
        
        # Paquetes del último mes
        from datetime import datetime, timedelta
        hoy = datetime.now()
        mes_pasado = hoy - timedelta(days=30)
        
        ultimo_mes = Paquete.objects.filter(
            fecha_creacion__gte=mes_pasado
        ).count()
        
        return Response({
            'total': total,
            'ultimo_mes': ultimo_mes,
            'por_estado': list(por_estado)
        })
    
    @action(detail=False, methods=['post'])
    def registrar_lote(self, request):
        paquetes_data = request.data.get('paquetes', [])
        
        if not paquetes_data:
            return Response(
                {'error': 'No se proporcionaron paquetes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paquetes_creados = []
        errores = []
        
        with transaction.atomic():
            for i, paquete_data in enumerate(paquetes_data):
                try:
                    serializer = PaqueteCreateSerializer(data=paquete_data)
                    if serializer.is_valid():
                        paquete = serializer.save()
                        
                        # Crear historial
                        HistorialPaquete.objects.create(
                            paquete=paquete,
                            estado_anterior='registrado',
                            estado_nuevo='registrado',
                            observacion='Paquete registrado en lote'
                        )
                        
                        paquetes_creados.append(paquete.codigo_seguimiento)
                    else:
                        errores.append({
                            'indice': i,
                            'errores': serializer.errors
                        })
                except Exception as e:
                    errores.append({
                        'indice': i,
                        'error': str(e)
                    })
        
        return Response({
            'paquetes_creados': paquetes_creados,
            'total_creados': len(paquetes_creados),
            'errores': errores,
            'total_errores': len(errores)
        })


class HistorialPaqueteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistorialPaquete.objects.all().select_related('paquete')
    serializer_class = HistorialPaqueteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        paquete_id = self.request.query_params.get('paquete_id')
        
        if paquete_id:
            queryset = queryset.filter(paquete_id=paquete_id)
        
        return queryset.order_by('-fecha_cambio')


class RutaPaqueteViewSet(viewsets.ModelViewSet):
    queryset = RutaPaquete.objects.all().select_related('paquete', 'vehiculo', 'conductor')
    serializer_class = RutaPaqueteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        paquete_id = self.request.query_params.get('paquete_id')
        
        if paquete_id:
            queryset = queryset.filter(paquete_id=paquete_id)
        
        return queryset.order_by('paquete', 'orden_en_ruta')
    
    @action(detail=True, methods=['post'])
    def completar_parada(self, request, pk=None):
        ruta = self.get_object()
        
        if ruta.completado:
            return Response(
                {'error': 'Esta parada ya está completada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ruta.completado = True
        ruta.fecha_llegada = timezone.now()
        ruta.save()
        
        # Actualizar el estado del paquete según el tipo de acción
        paquete = ruta.paquete
        paquete.estado = 'en_transito' if not ruta.completado else 'entregado'
        paquete.save()
        
        HistorialPaquete.objects.create(
            paquete=paquete,
            estado_anterior='en_reparto',
            estado_nuevo=paquete.estado,
            ubicacion=ruta.destino,
            observacion='Parada de ruta completada'
        )
        
        return Response({
            'mensaje': 'Parada completada exitosamente',
            'ruta': RutaPaqueteSerializer(ruta).data
        })
