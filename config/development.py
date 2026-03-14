"""
Development settings for Rapid Cash
Configuration optimisée pour le développement local HTTP
"""

from .settings import *

# Override pour développement local
DEBUG = True

# Hosts locaux explicites
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'testserver']

# FORCER HTTP en développement (pas de HTTPS)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_PROXY_SSL_HEADER = None

# Désactiver les headers de sécurité qui pourraient causer des problèmes
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Moins strict que 'DENY'

# Logging pour développement
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Message de bienvenue dans la console
print("""
DJANGO DEVELOPMENT MODE
Configuration: HTTP uniquement
URLs: http://localhost:8000 | http://127.0.0.1:8000
ATTENTION: Utiliser http:// (pas https://)
""")
