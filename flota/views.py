from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import TipoVehiculo, Vehiculo, MantenimientoVehiculo, RepuestoVehiculo, UsoRepuestoMantenimiento
from .serializers import (
    TipoVehiculoSerializer, VehiculoSerializer, VehiculoAsignacionSerializer,
    MantenimientoVehiculoSerializer, MantenimientoProgramadoSerializer,
    RepuestoVehiculoSerializer, UsoRepuestoMantenimientoSerializer,
    DashboardFlotaSerializer, VehiculoDetalleSerializer
)


class TipoVehiculoViewSet(viewsets.ModelViewSet):
    queryset = TipoVehiculo.objects.all()
    serializer_class = TipoVehiculoSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        tipos = self.get_queryset().filter(activo=True)
        serializer = self.get_serializer(tipos, many=True)
        return Response(serializer.data)


class VehiculoViewSet(viewsets.ModelViewSet):
    queryset = Vehiculo.objects.all()
    serializer_class = VehiculoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Vehiculo.objects.select_related('tipo', 'conductor_asignado__usuario')
        
        # Filtros
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_id=tipo)
        
        conductor = self.request.query_params.get('conductor')
        if conductor:
            queryset = queryset.filter(conductor_asignado_id=conductor)
        
        mantenimiento = self.request.query_params.get('mantenimiento')
        if mantenimiento:
            queryset = queryset.filter(estado_mantenimiento=mantenimiento)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def asignar_conductor(self, request, pk=None):
        vehiculo = self.get_object()
        conductor_id = request.data.get('conductor_id')
        
        if not conductor_id:
            return Response({'error': 'Conductor ID es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from conductores.models import Conductor
            conductor = Conductor.objects.get(id=conductor_id)
            
            # Verificar si el conductor ya tiene un vehículo asignado
            if Vehiculo.objects.filter(conductor_asignado=conductor).exclude(id=vehiculo.id).exists():
                return Response({'error': 'El conductor ya tiene un vehículo asignado'}, status=status.HTTP_400_BAD_REQUEST)
            
            vehiculo.conductor_asignado = conductor
            vehiculo.save()
            
            serializer = self.get_serializer(vehiculo)
            return Response(serializer.data)
            
        except Conductor.DoesNotExist:
            return Response({'error': 'Conductor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def desasignar_conductor(self, request, pk=None):
        vehiculo = self.get_object()
        vehiculo.conductor_asignado = None
        vehiculo.save()
        
        serializer = self.get_serializer(vehiculo)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def actualizar_kilometraje(self, request, pk=None):
        vehiculo = self.get_object()
        kilometraje = request.data.get('kilometraje')
        
        if not kilometraje:
            return Response({'error': 'Kilometraje es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            kilometraje = int(kilometraje)
            if kilometraje < vehiculo.kilometraje_actual:
                return Response({'error': 'El kilometraje no puede ser menor al actual'}, status=status.HTTP_400_BAD_REQUEST)
            
            vehiculo.kilometraje_actual = kilometraje
            vehiculo.save()
            
            serializer = self.get_serializer(vehiculo)
            return Response(serializer.data)
            
        except ValueError:
            return Response({'error': 'Kilometraje debe ser un número válido'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        vehiculos = self.get_queryset().filter(
            estado='operativo',
            estado_mantenimiento='en_servicio'
        )
        serializer = VehiculoAsignacionSerializer(vehiculos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def requieren_mantenimiento(self, request):
        vehiculos = self.get_queryset().filter(
            Q(estado_mantenimiento='mantenimiento_pendiente') |
            Q(estado_mantenimiento='atrasado')
        )
        serializer = self.get_serializer(vehiculos, many=True)
        return Response(serializer.data)


class MantenimientoVehiculoViewSet(viewsets.ModelViewSet):
    queryset = MantenimientoVehiculo.objects.all()
    serializer_class = MantenimientoVehiculoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = MantenimientoVehiculo.objects.select_related('vehiculo__tipo')
        
        # Filtros
        vehiculo = self.request.query_params.get('vehiculo')
        if vehiculo:
            queryset = queryset.filter(vehiculo_id=vehiculo)
        
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        tipo = self.request.query_params.get('tipo')
        if tipo:
            queryset = queryset.filter(tipo_mantenimiento=tipo)
        
        fecha_desde = self.request.query_params.get('fecha_desde')
        if fecha_desde:
            queryset = queryset.filter(fecha_programada__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        if fecha_hasta:
            queryset = queryset.filter(fecha_programada__lte=fecha_hasta)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def completar_mantenimiento(self, request, pk=None):
        mantenimiento = self.get_object()
        
        if mantenimiento.estado != 'pendiente':
            return Response({'error': 'Solo se pueden completar mantenimientos pendientes'}, status=status.HTTP_400_BAD_REQUEST)
        
        fecha_realizacion = request.data.get('fecha_realizacion')
        kilometraje_actual = request.data.get('kilometraje_actual')
        costo_mano_obra = request.data.get('costo_mano_obra', 0)
        duracion_dias = request.data.get('duracion_dias', 1)
        descripcion_trabajo = request.data.get('descripcion_trabajo_realizado', '')
        
        if not fecha_realizacion or not kilometraje_actual:
            return Response({'error': 'Fecha de realización y kilometraje actual son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            mantenimiento.fecha_realizacion = datetime.strptime(fecha_realizacion, '%Y-%m-%d').date()
            mantenimiento.kilometraje_actual = int(kilometraje_actual)
            mantenimiento.costo_mano_obra = float(costo_mano_obra)
            mantenimiento.duracion_dias = int(duracion_dias)
            mantenimiento.descripcion_trabajo_realizado = descripcion_trabajo
            mantenimiento.estado = 'completado'
            mantenimiento.save()
            
            # Actualizar el vehículo
            vehiculo = mantenimiento.vehiculo
            vehiculo.ultimo_mantenimiento = mantenimiento.fecha_realizacion
            vehiculo.kilometraje_actual = mantenimiento.kilometraje_actual
            vehiculo.estado_mantenimiento = 'en_servicio'
            vehiculo.save()
            
            serializer = self.get_serializer(mantenimiento)
            return Response(serializer.data)
            
        except ValueError as e:
            return Response({'error': f'Error en los datos: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        mantenimientos = self.get_queryset().filter(estado='pendiente')
        serializer = MantenimientoProgramadoSerializer(mantenimientos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def proximos(self, request):
        fecha_limite = timezone.now().date() + timedelta(days=7)
        mantenimientos = self.get_queryset().filter(
            estado='pendiente',
            fecha_programada__lte=fecha_limite
        )
        serializer = MantenimientoProgramadoSerializer(mantenimientos, many=True)
        return Response(serializer.data)


class RepuestoVehiculoViewSet(viewsets.ModelViewSet):
    queryset = RepuestoVehiculo.objects.all()
    serializer_class = RepuestoVehiculoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = RepuestoVehiculo.objects.select_related('tipo_vehiculo')
        
        # Filtros
        tipo_vehiculo = self.request.query_params.get('tipo_vehiculo')
        if tipo_vehiculo:
            queryset = queryset.filter(tipo_vehiculo_id=tipo_vehiculo)
        
        bajo_stock = self.request.query_params.get('bajo_stock')
        if bajo_stock == 'true':
            queryset = queryset.filter(cantidad_stock__lte=models.F('cantidad_minima'))
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def actualizar_stock(self, request, pk=None):
        repuesto = self.get_object()
        cantidad = request.data.get('cantidad')
        tipo = request.data.get('tipo')  # 'sumar' o 'restar'
        
        if not cantidad or not tipo:
            return Response({'error': 'Cantidad y tipo son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cantidad = int(cantidad)
            if tipo == 'sumar':
                repuesto.cantidad_stock += cantidad
            elif tipo == 'restar':
                if repuesto.cantidad_stock < cantidad:
                    return Response({'error': 'Stock insuficiente'}, status=status.HTTP_400_BAD_REQUEST)
                repuesto.cantidad_stock -= cantidad
            else:
                return Response({'error': 'Tipo debe ser "sumar" o "restar"'}, status=status.HTTP_400_BAD_REQUEST)
            
            repuesto.save()
            serializer = self.get_serializer(repuesto)
            return Response(serializer.data)
            
        except ValueError:
            return Response({'error': 'Cantidad debe ser un número válido'}, status=status.HTTP_400_BAD_REQUEST)


class UsoRepuestoMantenimientoViewSet(viewsets.ModelViewSet):
    queryset = UsoRepuestoMantenimiento.objects.all()
    serializer_class = UsoRepuestoMantenimientoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = UsoRepuestoMantenimiento.objects.select_related('repuesto', 'mantenimiento__vehiculo')
        
        mantenimiento = self.request.query_params.get('mantenimiento')
        if mantenimiento:
            queryset = queryset.filter(mantenimiento_id=mantenimiento)
        
        return queryset


class DashboardFlotaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        # Estadísticas generales
        total_vehiculos = Vehiculo.objects.count()
        vehiculos_operativos = Vehiculo.objects.filter(estado='operativo').count()
        vehiculos_mantenimiento = Vehiculo.objects.filter(estado='en_mantenimiento').count()
        vehiculos_fuera_servicio = Vehiculo.objects.filter(estado='fuera_servicio').count()
        
        # Mantenimientos
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=7)
        
        mantenimientos_pendientes = MantenimientoVehiculo.objects.filter(estado='pendiente').count()
        mantenimientos_proximos_7_dias = MantenimientoVehiculo.objects.filter(
            estado='pendiente',
            fecha_programada__lte=fecha_limite
        ).count()
        
        # Costos del mes actual
        primer_dia_mes = hoy.replace(day=1)
        costo_mantenimiento_mes = MantenimientoVehiculo.objects.filter(
            fecha_realizacion__gte=primer_dia_mes,
            estado='completado'
        ).aggregate(total=Sum('costo_mano_obra'))['total'] or 0
        
        # Consumo promedio de combustible
        promedio_consumo = Vehiculo.objects.filter(
            consumo_combustible_promedio__gt=0
        ).aggregate(promedio=Avg('consumo_combustible_promedio'))['promedio'] or 0
        
        data = {
            'total_vehiculos': total_vehiculos,
            'vehiculos_operativos': vehiculos_operativos,
            'vehiculos_mantenimiento': vehiculos_mantenimiento,
            'vehiculos_fuera_servicio': vehiculos_fuera_servicio,
            'mantenimientos_pendientes': mantenimientos_pendientes,
            'mantenimientos_proximos_7_dias': mantenimientos_proximos_7_dias,
            'costo_mantenimiento_mes': costo_mantenimiento_mes,
            'promedio_consumo_combustible': round(promedio_consumo, 2)
        }
        
        serializer = DashboardFlotaSerializer(data)
        return Response(serializer.data)
