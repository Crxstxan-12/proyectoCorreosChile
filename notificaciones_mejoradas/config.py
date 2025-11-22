# Configuración de notificaciones
NOTIFICATION_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'EMAIL_HOST': 'smtp.gmail.com',  # Configurar según tu proveedor
    'EMAIL_PORT': 587,
    'EMAIL_USE_TLS': True,
    'EMAIL_HOST_USER': 'tu-email@correoschile.cl',
    'EMAIL_HOST_PASSWORD': 'tu-contraseña',
    'DEFAULT_FROM_EMAIL': 'CorreosChile <no-reply@correoschile.cl>',
    
    # Configuración SMS (Twilio ejemplo)
    'SMS_PROVIDER': {
        'PROVIDER': 'twilio',
        'ACCOUNT_SID': 'tu-account-sid',
        'AUTH_TOKEN': 'tu-auth-token',
        'FROM_NUMBER': '+1234567890',
    },
    
    # Configuración WhatsApp (Twilio ejemplo)
    'WHATSAPP_PROVIDER': {
        'PROVIDER': 'twilio',
        'ACCOUNT_SID': 'tu-account-sid',
        'AUTH_TOKEN': 'tu-auth-token',
        'FROM_NUMBER': 'whatsapp:+1234567890',
    },
    
    # Límites y configuración
    'MAX_DAILY_NOTIFICATIONS': 10,
    'BUSINESS_HOURS_START': 8,  # 8 AM
    'BUSINESS_HOURS_END': 20,   # 8 PM
    'DEFAULT_TIMEZONE': 'America/Santiago',
}