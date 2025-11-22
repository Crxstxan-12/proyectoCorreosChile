from rest_framework import serializers
from .models import TipoVehiculo, Vehiculo, MantenimientoVehiculo, RepuestoVehiculo, UsoRepuestoMantenimiento
from conductores.models import Conductor


class TipoVehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoVehiculo
        fields = '__all__'


class VehiculoSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    conductor_nombre = serializers.SerializerMethodField(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    estado_mantenimiento_display = serializers.CharField(source='get_estado_mantenimiento_display', read_only=True)
    dias_ultimo_mantenimiento = serializers.SerializerMethodField(read_only=True)
    proximo_mantenimiento_km = serializers.SerializerMethodField(read_only=True)
    proximo_mantenimiento_fecha = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Vehiculo
        fields = [
            'id', 'patente', 'marca', 'modelo', 'anio', 'tipo', 'tipo_nombre',
            'capacidad_carga_kg', 'capacidad_volumen_m3', 'conductor_asignado',
            'conductor_nombre', 'estado', 'estado_display', 'kilometraje_actual',
            'estado_mantenimiento', 'estado_mantenimiento_display', 'ultimo_mantenimiento',
            'proximo_mantenimiento_km', 'proximo_mantenimiento_fecha',
            'dias_ultimo_mantenimiento', 'consumo_combustible_promedio',
            'numero_chasis', 'numero_motor', 'fecha_adquisicion', 'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    def get_conductor_nombre(self, obj):
        if obj.conductor_asignado:
            return f"{obj.conductor_asignado.usuario.first_name} {obj.conductor_asignado.usuario.last_name}"
        return "Sin asignar"
    
    def get_dias_ultimo_mantenimiento(self, obj):
        if obj.ultimo_mantenimiento:
            from datetime import date
            dias = (date.today() - obj.ultimo_mantenimiento).days
            return dias
        return None
    
    def get_proximo_mantenimiento_km(self, obj):
        if obj.kilometraje_actual and obj.tipo.kilometraje_mantenimiento:
            return obj.kilometraje_actual + (obj.tipo.kilometraje_mantenimiento - (obj.kilometraje_actual % obj.tipo.kilometraje_mantenimiento))
        return None
    
    def get_proximo_mantenimiento_fecha(self, obj):
        if obj.ultimo_mantenimiento and obj.tipo.dias_mantenimiento:
            from datetime import timedelta
            return obj.ultimo_mantenimiento + timedelta(days=obj.tipo.dias_mantenimiento)
        return None


class VehiculoAsignacionSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    conductor_actual = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Vehiculo
        fields = ['id', 'patente', 'marca', 'modelo', 'tipo_nombre', 'conductor_actual', 'estado']
    
    def get_conductor_actual(self, obj):
        if obj.conductor_asignado:
            return {
                'id': obj.conductor_asignado.id,
                'nombre': f"{obj.conductor_asignado.usuario.first_name} {obj.conductor_asignado.usuario.last_name}",
                'telefono': obj.conductor_asignado.telefono
            }
        return None


class MantenimientoVehiculoSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='vehiculo.patente', read_only=True)
    tipo_mantenimiento_display = serializers.CharField(source='get_tipo_mantenimiento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    costo_total = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MantenimientoVehiculo
        fields = [
            'id', 'vehiculo', 'vehiculo_patente', 'tipo_mantenimiento',
            'tipo_mantenimiento_display', 'descripcion', 'fecha_programada',
            'fecha_realizacion', 'kilometraje_actual', 'estado', 'estado_display',
            'costo_mano_obra', 'costo_repuestos', 'costo_total', 'taller',
            'descripcion_trabajo_realizado', 'duracion_dias', 'proveedor',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion', 'costo_repuestos']
    
    def get_costo_total(self, obj):
        return obj.costo_mano_obra + obj.costo_repuestos


class MantenimientoProgramadoSerializer(serializers.ModelSerializer):
    vehiculo_patente = serializers.CharField(source='vehiculo.patente', read_only=True)
    vehiculo_marca = serializers.CharField(source='vehiculo.marca', read_only=True)
    vehiculo_modelo = serializers.CharField(source='vehiculo.modelo', read_only=True)
    dias_para_mantenimiento = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MantenimientoVehiculo
        fields = [
            'id', 'vehiculo', 'vehiculo_patente', 'vehiculo_marca', 'vehiculo_modelo',
            'tipo_mantenimiento', 'descripcion', 'fecha_programada', 'dias_para_mantenimiento'
        ]
    
    def get_dias_para_mantenimiento(self, obj):
        from datetime import date
        if obj.fecha_programada:
            dias = (obj.fecha_programada - date.today()).days
            return max(0, dias)
        return None


class RepuestoVehiculoSerializer(serializers.ModelSerializer):
    tipo_vehiculo_nombre = serializers.CharField(source='tipo_vehiculo.nombre', read_only=True)
    
    class Meta:
        model = RepuestoVehiculo
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'tipo_vehiculo',
            'tipo_vehiculo_nombre', 'cantidad_stock', 'cantidad_minima',
            'precio_unitario', 'proveedor', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class UsoRepuestoMantenimientoSerializer(serializers.ModelSerializer):
    repuesto_nombre = serializers.CharField(source='repuesto.nombre', read_only=True)
    repuesto_codigo = serializers.CharField(source='repuesto.codigo', read_only=True)
    mantenimiento_id = serializers.IntegerField(source='mantenimiento.id', read_only=True)
    costo_total = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = UsoRepuestoMantenimiento
        fields = [
            'id', 'repuesto', 'repuesto_nombre', 'repuesto_codigo', 'mantenimiento_id',
            'cantidad_usada', 'costo_unitario', 'costo_total', 'fecha_uso'
        ]
        read_only_fields = ['fecha_uso']
    
    def get_costo_total(self, obj):
        return obj.cantidad_usada * obj.costo_unitario


class DashboardFlotaSerializer(serializers.Serializer):
    total_vehiculos = serializers.IntegerField()
    vehiculos_operativos = serializers.IntegerField()
    vehiculos_mantenimiento = serializers.IntegerField()
    vehiculos_fuera_servicio = serializers.IntegerField()
    mantenimientos_pendientes = serializers.IntegerField()
    mantenimientos_proximos_7_dias = serializers.IntegerField()
    costo_mantenimiento_mes = serializers.DecimalField(max_digits=10, decimal_places=2)
    promedio_consumo_combustible = serializers.FloatField()


class VehiculoDetalleSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='tipo.nombre', read_only=True)
    conductor_nombre = serializers.SerializerMethodField(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    estado_mantenimiento_display = serializers.CharField(source='get_estado_mantenimiento_display', read_only=True)
    ultimos_mantenimientos = serializers.SerializerMethodField(read_only=True)
    mantenimientos_pendientes = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Vehiculo
        fields = [
            'id', 'patente', 'marca', 'modelo', 'anio', 'tipo', 'tipo_nombre',
            'capacidad_carga_kg', 'capacidad_volumen_m3', 'conductor_asignado',
            'conductor_nombre', 'estado', 'estado_display', 'kilometraje_actual',
            'estado_mantenimiento', 'estado_mantenimiento_display', 'ultimo_mantenimiento',
            'proximo_mantenimiento_km', 'proximo_mantenimiento_fecha',
            'consumo_combustible_promedio', 'numero_chasis', 'numero_motor',
            'fecha_adquisicion', 'ultimos_mantenimientos', 'mantenimientos_pendientes'
        ]
    
    def get_conductor_nombre(self, obj):
        if obj.conductor_asignado:
            return f"{obj.conductor_asignado.usuario.first_name} {obj.conductor_asignado.usuario.last_name}"
        return "Sin asignar"
    
    def get_ultimos_mantenimientos(self, obj):
        mantenimientos = obj.mantenimientos.order_by('-fecha_realizacion')[:5]
        return MantenimientoVehiculoSerializer(mantenimientos, many=True).data
    
    def get_mantenimientos_pendientes(self, obj):
        mantenimientos = obj.mantenimientos.filter(estado='pendiente').order_by('fecha_programada')[:3]
        return MantenimientoProgramadoSerializer(mantenimientos, many=True).data