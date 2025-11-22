from rest_framework import serializers
from .models import TipoPaquete, Remitente, Destinatario, Paquete, HistorialPaquete, RutaPaquete, PuntoEntrega


class TipoPaqueteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPaquete
        fields = '__all__'


class RemitenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Remitente
        fields = '__all__'


class DestinatarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destinatario
        fields = '__all__'


class PuntoEntregaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoEntrega
        fields = '__all__'


class HistorialPaqueteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistorialPaquete
        fields = '__all__'


class RutaPaqueteSerializer(serializers.ModelSerializer):
    punto_entrega_nombre = serializers.CharField(source='punto_entrega.nombre', read_only=True)
    
    class Meta:
        model = RutaPaquete
        fields = ['id', 'orden', 'punto_entrega', 'punto_entrega_nombre', 
                  'tipo_accion', 'fecha_hora_estimada', 'fecha_hora_real', 'completado', 'notas']


class PaqueteListSerializer(serializers.ModelSerializer):
    remitente_nombre = serializers.CharField(source='remitente.nombre_completo', read_only=True)
    destinatario_nombre = serializers.CharField(source='destinatario.nombre_completo', read_only=True)
    tipo_paquete_nombre = serializers.CharField(source='tipo_paquete.nombre', read_only=True)
    
    class Meta:
        model = Paquete
        fields = ['id', 'codigo_seguimiento', 'remitente_nombre', 'destinatario_nombre',
                  'tipo_paquete_nombre', 'estado', 'peso_kg', 'monto_total', 'fecha_creacion']


class PaqueteDetailSerializer(serializers.ModelSerializer):
    remitente = RemitenteSerializer(read_only=True)
    destinatario = DestinatarioSerializer(read_only=True)
    tipo_paquete = TipoPaqueteSerializer(read_only=True)
    punto_entrega = PuntoEntregaSerializer(read_only=True)
    historial = HistorialPaqueteSerializer(many=True, read_only=True, source='historialpaquete_set')
    ruta = RutaPaqueteSerializer(many=True, read_only=True, source='rutapaquete_set')
    
    class Meta:
        model = Paquete
        fields = '__all__'


class PaqueteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paquete
        fields = ['tipo_paquete', 'remitente', 'destinatario', 'peso_kg', 
                  'largo_cm', 'ancho_cm', 'alto_cm', 'descripcion_contenido',
                  'valor_declarado', 'prioridad', 'forma_pago']

    def create(self, validated_data):
        paquete = Paquete.objects.create(**validated_data)
        return paquete


class SeguimientoPaqueteSerializer(serializers.ModelSerializer):
    remitente = RemitenteSerializer(read_only=True)
    destinatario = DestinatarioSerializer(read_only=True)
    historial = HistorialPaqueteSerializer(many=True, read_only=True, source='historialpaquete_set')
    ruta = RutaPaqueteSerializer(many=True, read_only=True, source='rutapaquete_set')
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Paquete
        fields = ['codigo_seguimiento', 'estado', 'estado_display', 'fecha_creacion',
                  'remitente', 'destinatario', 'peso_kg', 'monto_total',
                  'historial', 'ruta']


class ActualizarEstadoSerializer(serializers.Serializer):
    nuevo_estado = serializers.ChoiceField(choices=Paquete.ESTADO_PAQUETE)
    ubicacion = serializers.CharField(max_length=200, required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def validate_nuevo_estado(self, value):
        # Validar que el estado es válido para la transición
        paquete = self.context['paquete']
        
        # Definir transiciones válidas
        transiciones_validas = {
            'registrado': ['en_almacen', 'en_transito'],
            'en_almacen': ['en_transito', 'en_reparto', 'listo_para_retiro'],
            'en_transito': ['en_almacen', 'en_reparto', 'listo_para_retiro'],
            'en_reparto': ['entregado', 'en_almacen'],
            'listo_para_retiro': ['entregado', 'en_almacen'],
            'entregado': [],
            'entrega_fallida': ['en_reparto', 'en_almacen'],
            'devuelto': ['en_almacen'],
            'perdido': [],
            'danado': []
        }
        
        estado_actual = paquete.estado
        if value not in transiciones_validas.get(estado_actual, []):
            raise serializers.ValidationError(
                f"No se puede cambiar del estado '{estado_actual}' a '{value}'"
            )
        
        return value


class GenerarEtiquetaSerializer(serializers.ModelSerializer):
    remitente = RemitenteSerializer(read_only=True)
    destinatario = DestinatarioSerializer(read_only=True)
    tipo_paquete = TipoPaqueteSerializer(read_only=True)
    codigo_qr = serializers.SerializerMethodField()
    codigo_barras = serializers.SerializerMethodField()
    
    class Meta:
        model = Paquete
        fields = ['codigo_seguimiento', 'remitente', 'destinatario', 'tipo_paquete',
                  'peso_kg', 'largo_cm', 'ancho_cm', 'alto_cm', 'codigo_qr', 'codigo_barras']
    
    def get_codigo_qr(self, obj):
        # Generar código QR (se implementará con la librería correspondiente)
        return f"QR_{obj.codigo_seguimiento}"
    
    def get_codigo_barras(self, obj):
        # Generar código de barras (se implementará con la librería correspondiente)
        return f"BC_{obj.codigo_seguimiento}"