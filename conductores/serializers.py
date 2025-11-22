from rest_framework import serializers
from .models import Conductor, RutaConductor, EnvioRuta, IncidenciaConductor, MetricasConductor
from envios.models import Envio
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializador para el modelo User"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class ConductorSerializer(serializers.ModelSerializer):
    """Serializador principal para el modelo Conductor"""
    usuario = UserSerializer(read_only=True)
    nombre_completo = serializers.CharField(read_only=True)
    esta_disponible = serializers.BooleanField(read_only=True)
    licencia_vencida = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Conductor
        fields = [
            'id', 'usuario', 'nombre_completo', 'telefono', 'licencia_conducir',
            'fecha_vencimiento_licencia', 'vehiculo_asignado', 'placa_vehiculo',
            'estado', 'esta_disponible', 'licencia_vencida', 'latitud_actual',
            'longitud_actual', 'ultima_actualizacion_ubicacion', 'dispositivo_id',
            'token_notificacion', 'app_version', 'total_envios_entregados',
            'total_kilometros_recorridos', 'hora_inicio_jornada', 'hora_fin_jornada',
            'activo', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']


class ConductorUbicacionSerializer(serializers.Serializer):
    """Serializador para actualizar ubicación del conductor"""
    latitud = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitud = serializers.DecimalField(max_digits=11, decimal_places=8)
    
    def update(self, instance, validated_data):
        instance.actualizar_ubicacion(
            validated_data['latitud'],
            validated_data['longitud']
        )
        return instance


class ConductorEstadoSerializer(serializers.Serializer):
    """Serializador para cambiar estado del conductor"""
    estado = serializers.ChoiceField(choices=Conductor.ESTADOS_CONDUCTOR)
    
    def update(self, instance, validated_data):
        instance.cambiar_estado(validated_data['estado'])
        return instance


class EnvioSerializer(serializers.ModelSerializer):
    """Serializador básico para envíos"""
    remitente_nombre = serializers.CharField(source='remitente.get_full_name', read_only=True)
    destinatario_nombre = serializers.CharField(source='destinatario.get_full_name', read_only=True)
    
    class Meta:
        model = Envio
        fields = [
            'id', 'codigo', 'remitente_nombre', 'destinatario_nombre',
            'direccion_destino', 'telefono_destinatario', 'estado',
            'fecha_creacion', 'fecha_estimada_entrega'
        ]


class EnvioRutaSerializer(serializers.ModelSerializer):
    """Serializador para envíos en ruta"""
    envio = EnvioSerializer(read_only=True)
    direccion_formateada = serializers.SerializerMethodField()
    
    class Meta:
        model = EnvioRuta
        fields = [
            'id', 'envio', 'orden_entrega', 'estado', 'direccion_formateada',
            'fecha_intento_entrega', 'motivo_fallo', 'latitud_entrega',
            'longitud_entrega', 'notas'
        ]
        read_only_fields = ['id', 'fecha_intento_entrega']
    
    def get_direccion_formateada(self, obj):
        """Retorna la dirección formateada del envío"""
        if obj.envio:
            return f"{obj.envio.direccion_destino}"
        return ""


class EnvioRutaEntregaSerializer(serializers.Serializer):
    """Serializador para registrar entrega de envío"""
    estado = serializers.ChoiceField(choices=EnvioRuta.ESTADOS_ENVIO_RUTA)
    firma_digital = serializers.CharField(required=False, allow_blank=True)
    motivo_fallo = serializers.CharField(required=False, allow_blank=True)
    latitud = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitud = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    notas = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        nuevo_estado = validated_data['estado']
        
        if nuevo_estado == 'entregado':
            instance.marcar_entregado(
                firma_digital=validated_data.get('firma_digital'),
                latitud=validated_data.get('latitud'),
                longitud=validated_data.get('longitud')
            )
        elif nuevo_estado == 'fallido':
            instance.marcar_fallido(
                motivo=validated_data.get('motivo_fallo', 'No especificado'),
                latitud=validated_data.get('latitud'),
                longitud=validated_data.get('longitud')
            )
        else:
            instance.estado = nuevo_estado
            instance.notas = validated_data.get('notas', '')
            instance.save()
        
        return instance


class RutaConductorSerializer(serializers.ModelSerializer):
    """Serializador para rutas de conductores"""
    conductor = ConductorSerializer(read_only=True)
    envios_ruta = EnvioRutaSerializer(many=True, read_only=True)
    progreso = serializers.ReadOnlyField()
    
    class Meta:
        model = RutaConductor
        fields = [
            'id', 'conductor', 'fecha', 'nombre_ruta', 'descripcion',
            'estado', 'total_envios', 'envios_entregados', 'envios_fallidos',
            'distancia_total_km', 'tiempo_estimado_minutos', 'progreso',
            'hora_inicio', 'hora_fin', 'envios_ruta', 'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']


class RutaConductorCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear rutas de conductores"""
    envios_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    
    class Meta:
        model = RutaConductor
        fields = [
            'conductor', 'fecha', 'nombre_ruta', 'descripcion',
            'distancia_total_km', 'tiempo_estimado_minutos', 'envios_ids'
        ]
    
    def create(self, validated_data):
        envios_ids = validated_data.pop('envios_ids', [])
        
        # Crear la ruta
        ruta = RutaConductor.objects.create(**validated_data)
        
        # Asignar envíos a la ruta
        for index, envio_id in enumerate(envios_ids):
            try:
                envio = Envio.objects.get(id=envio_id)
                EnvioRuta.objects.create(
                    ruta=ruta,
                    envio=envio,
                    orden_entrega=index + 1
                )
            except Envio.DoesNotExist:
                continue
        
        # Actualizar contadores
        ruta.total_envios = len(envios_ids)
        ruta.save(update_fields=['total_envios'])
        
        return ruta


class IncidenciaConductorSerializer(serializers.ModelSerializer):
    """Serializador para incidencias de conductores"""
    conductor = ConductorSerializer(read_only=True)
    conductor_id = serializers.PrimaryKeyRelatedField(
        queryset=Conductor.objects.all(),
        source='conductor',
        write_only=True
    )
    
    class Meta:
        model = IncidenciaConductor
        fields = [
            'id', 'conductor', 'conductor_id', 'titulo', 'descripcion',
            'tipo', 'latitud', 'longitud', 'estado', 'foto1', 'foto2',
            'foto3', 'envio_afectado', 'fecha_reporte', 'fecha_resolucion',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_reporte', 'fecha_creacion', 'fecha_actualizacion']


class MetricasConductorSerializer(serializers.ModelSerializer):
    """Serializador para métricas de conductores"""
    conductor = ConductorSerializer(read_only=True)
    conductor_id = serializers.PrimaryKeyRelatedField(
        queryset=Conductor.objects.all(),
        source='conductor',
        write_only=True
    )
    
    class Meta:
        model = MetricasConductor
        fields = [
            'id', 'conductor', 'conductor_id', 'fecha', 'total_envios_entregados',
            'total_envios_fallidos', 'total_kilometros_recorridos',
            'tiempo_total_trabajado_minutos', 'eficiencia_entregas',
            'tiempo_promedio_entrega_minutos', 'total_incidencias_reportadas',
            'puntuacion_general', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'puntuacion_general', 'fecha_creacion', 'fecha_actualizacion']


class LoginSerializer(serializers.Serializer):
    """Serializador para login de conductores"""
    username = serializers.CharField()
    password = serializers.CharField()
    dispositivo_id = serializers.CharField(required=False)
    token_notificacion = serializers.CharField(required=False)


class CambiarPasswordSerializer(serializers.Serializer):
    """Serializador para cambiar contraseña"""
    password_actual = serializers.CharField()
    password_nuevo = serializers.CharField(min_length=8)
    password_confirmacion = serializers.CharField(min_length=8)
    
    def validate(self, attrs):
        if attrs['password_nuevo'] != attrs['password_confirmacion']:
            raise serializers.ValidationError("Las contraseñas nuevas no coinciden")
        return attrs