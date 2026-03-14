pyth#!/usr/bin/env python
"""
Test et diagnostic du problème de dashboard Django
"""

import os
import sys

def diagnose_dashboard_issue():
    """Diagnostiquer le problème de dashboard"""
    
    print("🔍 DIAGNOSTIC PROBLÈME DASHBOARD DJANGO")
    print("=" * 55)
    
    # Configuration Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    try:
        import django
        django.setup()
        
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from core.views import dashboard_view
        
        print("\n📋 Configuration:")
        print("   Settings module: config.settings")
        print("   Django version:", django.get_version())
        
        print("\n👥 Test des modèles:")
        
        User = get_user_model()
        
        # Vérifier les modèles requis
        try:
            from operations.models import Operation, Caisse
            print("   ✅ Modèles operations: Importés")
            
            # Test de requête simple
            count_operations = Operation.objects.count()
            print(f"   ✅ Operations: {count_operations} trouvées")
            
            count_caisses = Caisse.objects.count()
            print(f"   ✅ Caisses: {count_caisses} trouvées")
            
        except Exception as e:
            print(f"   ❌ Modèles operations: {e}")
        
        try:
            from finance.models import Expense
            print("   ✅ Modèle finance: Importé")
            
            count_expenses = Expense.objects.count()
            print(f"   ✅ Expenses: {count_expenses} trouvées")
            
        except Exception as e:
            print(f"   ❌ Modèle finance: {e}")
        
        try:
            from finance.models import PartnerContract
            print("   ✅ Modèle PartnerContract: Importé")
            
            count_contracts = PartnerContract.objects.count()
            print(f"   ✅ PartnerContracts: {count_contracts} trouvés")
            
        except Exception as e:
            print(f"   ❌ Modèle PartnerContract: {e}")
        
        print("\n🧪 Test de la vue dashboard:")
        
        # Créer un utilisateur de test
        test_user = User.objects.filter(role='ADMIN').first()
        
        if test_user:
            print(f"   ✅ Utilisateur de test: {test_user.username}")
            
            # Créer une requête factice
            factory = RequestFactory()
            request = factory.get('/')
            request.user = test_user
            
            # Tester la vue
            try:
                response = dashboard_view(request)
                print(f"   ✅ Vue dashboard: Status {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ Dashboard fonctionne correctement")
                else:
                    print(f"   ❌ Dashboard erreur: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Erreur vue dashboard: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ❌ Aucun utilisateur ADMIN trouvé pour le test")
        
        print("\n🔧 Vérifications manuelles:")
        print("   1. Vérifier les logs Django pour l'erreur 500")
        print("   2. Vérifier la console du navigateur (F12)")
        print("   3. Tester avec un utilisateur différent")
        print("   4. Vérifier les permissions des fichiers")
        
        print("\n💡 Si erreur 500 persiste:")
        print("   - Démarrer avec DEBUG=True pour voir l'erreur")
        print("   - Vérifier les imports dans la vue")
        print("   - Vérifier les relations entre modèles")
        print("   - Tester la vue en isolation")
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnose_dashboard_issue()
