# Integración E-commerce - CorreosChile

Este módulo permite integrar el sistema de CorreosChile con plataformas de e-commerce como Shopify, Amazon, WooCommerce, PrestaShop y plataformas personalizadas.

## Características

### 1. Plataformas Soportadas
- **Shopify**: Integración completa con webhooks
- **Amazon**: (En desarrollo)
- **WooCommerce**: (En desarrollo)
- **PrestaShop**: (En desarrollo)
- **Personalizado**: API REST para integraciones custom

### 2. Funcionalidades

#### Gestión de Pedidos
- Recepción automática de pedidos desde plataformas e-commerce
- Creación automática de envíos en el sistema
- Asignación de códigos de seguimiento únicos
- Gestión de múltiples productos por pedido

#### Webhooks
- Recepción de eventos en tiempo real
- Verificación de firmas HMAC para seguridad
- Logs detallados de todos los webhooks recibidos
- Manejo de errores y reintentos

#### Sincronización de Estados
- Actualización automática de estados de envío
- Notificaciones al cliente sobre cambios de estado
- Integración con el sistema de notificaciones existente

## Configuración

### 1. Shopify

1. **Crear plataforma en el sistema**:
   - Ir a "E-commerce > Configurar"
   - Seleccionar "Shopify" como tipo
   - Ingresar nombre de la tienda y URL
   - Configurar API Key y Webhook Secret

2. **Configurar webhooks en Shopify**:
   - Ir a Settings > Notifications > Webhooks
   - Agregar los siguientes eventos:
     - `orders/create` - URL: `https://tudominio.com/ecommerce/webhook/shopify/{id}/`
     - `orders/updated` - URL: `https://tudominio.com/ecommerce/webhook/shopify/{id}/`
     - `orders/cancelled` - URL: `https://tudominio.com/ecommerce/webhook/shopify/{id}/`
   - Configurar el Webhook Secret para seguridad

3. **Obtener credenciales**:
   - API Key: Desde Shopify Partners o App Privada
   - Webhook Secret: Generado automáticamente por Shopify

### 2. Amazon (Próximamente)

### 3. WooCommerce (Próximamente)

### 4. PrestaShop (Próximamente)

## API REST

### Endpoints

#### Webhook Shopify
```
POST /ecommerce/webhook/shopify/{plataforma_id}/
Headers:
  X-Shopify-Topic: orders/create
  X-Shopify-Hmac-Sha256: {signature}
  Content-Type: application/json

Body: JSON con datos del pedido
```

#### Administración de Plataformas
```
GET /ecommerce/ - Lista de pedidos
GET /ecommerce/configurar/ - Configuración de plataformas
POST /ecommerce/configurar/ - Crear/actualizar plataforma
```

## Modelos de Datos

### PlataformaEcommerce
- `nombre`: Nombre de la tienda
- `tipo`: Tipo de plataforma (shopify, amazon, etc.)
- `api_key`: Clave API de la plataforma
- `api_secret`: Secreto API (opcional)
- `webhook_secret`: Secreto para webhooks
- `store_url`: URL de la tienda
- `esta_activa`: Estado de la plataforma
- `usuario`: Usuario propietario

### PedidoEcommerce
- `plataforma`: Plataforma de origen
- `pedido_id_externo`: ID del pedido en la plataforma
- `numero_orden`: Número de orden visible
- `cliente_nombre`: Nombre del cliente
- `cliente_email`: Email del cliente
- `direccion_entrega`: Dirección de entrega
- `total`: Monto total del pedido
- `estado`: Estado del pedido
- `envio`: Envío asociado en el sistema
- `datos_raw`: Datos completos del pedido

### ProductoPedido
- `pedido`: Pedido al que pertenece
- `sku`: Código del producto
- `nombre`: Nombre del producto
- `cantidad`: Cantidad ordenada
- `precio_unitario`: Precio por unidad
- `peso_kg`: Peso del producto
- `dimensiones`: Dimensiones del producto

### WebhookLog
- `plataforma`: Plataforma de origen
- `evento_tipo`: Tipo de evento recibido
- `evento_id`: ID del evento
- `nivel`: Nivel de log (info, advertencia, error)
- `mensaje`: Mensaje descriptivo
- `datos_recibidos`: Datos del webhook
- `datos_procesados`: Resultado del procesamiento
- `ip_origen`: IP del origen
- `procesado_exitoso`: Si se procesó correctamente

## Flujo de Trabajo

1. **Recepción de Pedido**:
   - Plataforma envía webhook con datos del pedido
   - Sistema verifica firma y autenticidad
   - Se crea el pedido en la base de datos
   - Se genera un envío asociado
   - Se notifica al administrador

2. **Procesamiento de Envío**:
   - El pedido aparece en el panel de administración
   - Se pueden procesar los productos individualmente
   - Se generan códigos de bulto automáticamente
   - El envío se integra con el sistema de seguimiento

3. **Actualización de Estado**:
   - Cuando el envío cambia de estado
   - Se actualiza el estado del pedido e-commerce
   - Se notifica al cliente (si está configurado)

## Seguridad

- Verificación de firmas HMAC para webhooks
- Autenticación requerida para acceso a datos
- Logs detallados de todas las operaciones
- Validación de datos de entrada
- Manejo seguro de credenciales API

## Monitoreo y Mantenimiento

- Panel de administración con estadísticas
- Logs detallados de errores y eventos
- Alertas para fallos en procesamiento
- Métricas de rendimiento por plataforma

## Próximas Mejoras

- [ ] Integración con Amazon MWS/SP-API
- [ ] Integración con WooCommerce REST API
- [ ] Integración con PrestaShop WebService
- [ ] Sincronización bidireccional de estados
- [ ] Panel de métricas avanzadas
- [ ] Sistema de reintentos automáticos
- [ ] Notificaciones por email de fallos
- [ ] API REST completa para integraciones