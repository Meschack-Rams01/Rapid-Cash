#!/usr/bin/env python
"""
Script de développement Django avec configuration HTTP sécurisée
"""

import os
import sys
import subprocess

def run_development_server():
    """Lancer le serveur de développement avec la bonne configuration"""
    
    print("🚀 DÉMARRAGE SERVEUR DJANGO - MODE DÉVELOPPEMENT")
    print("=" * 50)
    
    # Vérifier la configuration
    print("📋 Vérification de la configuration...")
    
    # Forcer les settings de développement
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.development')
    
    try:
        import django
        django.setup()
        
        from django.conf import settings
        
        # Vérifications critiques
        checks = {
            'DEBUG': settings.DEBUG,
            'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
            'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
            'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
            'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
        }
        
        print("✅ Configuration vérifiée:")
        for key, value in checks.items():
            status = "✅" if (key == 'DEBUG' and value) or (key.startswith('SECURE_') and not value) else "❌"
            print(f"   {status} {key}: {value}")
        
        print("\n🌐 Démarrage du serveur...")
        print("   URL: http://localhost:8000")
        print("   URL: http://127.0.0.1:8000")
        print("\n⚠️  IMPORTANT:")
        print("   - Utiliser http:// (pas https://)")
        print("   - Mode navigation privée si problème")
        print("   - Arrêt: CTRL+C")
        print("\n" + "=" * 50)
        
        # Démarrer le serveur
        subprocess.run([sys.executable, 'manage.py', 'runserver'], check=True)
        
    except ImportError as e:
        print(f"❌ Erreur d'import Django: {e}")
        print("💡 Solution: pip install django djangorestframework django-htmx")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == '__main__':
    run_development_server()
