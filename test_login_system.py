#!/usr/bin/env python
"""
Quick Test Script for Login System
Run: python test_login_system.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import AuditLog
import pyotp

User = get_user_model()

def test_basic_login():
    """Test basic login functionality"""
    print("\n" + "="*50)
    print("TEST 1: Basic Login")
    print("="*50)
    
    # Create test user
    try:
        user = User.objects.get(username='test_admin')
    except User.DoesNotExist:
        user = User.objects.create_user(username='test_admin', password='admin123', role='ADMIN')
    
    client = Client()
    
    # Test successful login (with trailing slash)
    response = client.post('/login/', {'username': 'test_admin', 'password': 'admin123'}, follow=True)
    print(f"Login response final: {response.status_code}")
    
    # Check if logged in by accessing dashboard
    response = client.get('/dashboard/')
    print(f"Dashboard access: {response.status_code} (200 = logged in)")
    
    # Check audit log
    logs = AuditLog.objects.filter(user=user, action='LOGIN').order_by('-timestamp')
    if logs.exists():
        print(f"Audit log created: {logs.first().details}")
    else:
        print("ERROR: No audit log found")
    
    # Logout
    client.post('/logout/')
    print("Logged out")

def test_failed_login():
    """Test failed login logging"""
    print("\n" + "="*50)
    print("TEST 2: Failed Login Logging")
    print("="*50)
    
    client = Client()
    
    # Clear old failed logs
    AuditLog.objects.filter(action='LOGIN_FAILED').delete()
    
    # Test wrong password
    response = client.post('/login/', {'username': 'test_admin', 'password': 'wrongpass'}, follow=True)
    print(f"Failed login response final: {response.status_code}")
    
    # Check audit log
    logs = AuditLog.objects.filter(action='LOGIN_FAILED').order_by('-timestamp')
    if logs.exists():
        print(f"Failed login logged: {logs.first().details}")
    else:
        print("ERROR: No failed login audit log found")

def test_two_fa_flow():
    """Test 2FA flow"""
    print("\n" + "="*50)
    print("TEST 3: Two-Factor Authentication")
    print("="*50)
    
    # Create 2FA user
    try:
        user = User.objects.get(username='test_2fa')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='test_2fa', 
            password='2fa123', 
            role='AGENT',
            totp_secret='JBSWY3DPEHPK3PXP',
            is_2fa_enabled=True
        )
    
    client = Client()
    
    # Step 1: Login - should redirect to 2FA
    response = client.post('/login/', {'username': 'test_2fa', 'password': '2fa123'}, follow=False)
    print(f"2FA user login: {response.status_code}")
    
    if response.status_code == 302 and response.url and 'two-factor' in response.url:
        print(f"Redirected to 2FA: {response.url}")
        
        # Step 2: Generate valid TOTP
        totp = pyotp.TOTP('JBSWY3DPEHPK3PXP')
        valid_code = totp.now()
        print(f"Generated TOTP code: {valid_code}")
        
        # Step 3: Verify TOTP
        response = client.post('/two-factor/verify/', {'otp_code': valid_code}, follow=False)
        print(f"2FA verification: {response.status_code}")
        
        if response.status_code in [302, 303]:
            print(f"2FA passed, redirect to: {response.url}")
    else:
        print(f"ERROR: Did not redirect to 2FA. URL was: {response.url if hasattr(response, 'url') else 'N/A'}")

def test_session_regeneration():
    """Test session regeneration on login"""
    print("\n" + "="*50)
    print("TEST 4: Session Regeneration")
    print("="*50)
    
    client = Client()
    
    # Get initial session
    response = client.get('/login/')
    initial_session_key = client.session.session_key
    print(f"Initial session key: {initial_session_key}")
    
    # Login
    client.post('/login/', {'username': 'test_admin', 'password': 'admin123'}, follow=False)
    
    # Check new session
    new_session_key = client.session.session_key
    print(f"New session key: {new_session_key}")
    
    if initial_session_key != new_session_key:
        print("Session regenerated (security fix)")
    else:
        print("ERROR: Session not regenerated")

def test_rate_limiting():
    """Test rate limiting"""
    print("\n" + "="*50)
    print("TEST 5: Rate Limiting (Axes)")
    print("="*50)
    
    from django.conf import settings
    
    if hasattr(settings, 'AXES_ENABLED'):
        print(f"Axes enabled: {settings.AXES_ENABLED}")
        print(f"Failure limit: {settings.AXES_FAILURE_LIMIT}")
        print(f"Lockout duration: {settings.AXES_LOCK_OUT_DURATION} minutes")
    else:
        print("ERROR: Axes not configured")

if __name__ == '__main__':
    print("\n" + "#"*50)
    print("# RAPID CASH LOGIN SYSTEM TESTS")
    print("#"*50)
    
    try:
        test_basic_login()
        test_failed_login()
        test_two_fa_flow()
        test_session_regeneration()
        test_rate_limiting()
        
        print("\n" + "#"*50)
        print("# ALL TESTS COMPLETED")
        print("#"*50 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
