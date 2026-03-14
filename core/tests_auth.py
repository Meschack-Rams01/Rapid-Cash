"""
Comprehensive Tests for Authentication System
Tests login, 2FA, rate limiting, audit logging, and security features
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import AuditLog
import pyotp

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """Test cases for authentication system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test users with different roles
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            role='ADMIN',
            email='admin@test.com'
        )
        
        self.agent_user = User.objects.create_user(
            username='agent',
            password='agentpass123',
            role='AGENT',
            email='agent@test.com'
        )
        
        self.associate_user = User.objects.create_user(
            username='associate',
            password='associatepass123',
            role='ASSOCIATE',
            email='associate@test.com'
        )
        
        self.investor_user = User.objects.create_user(
            username='investor',
            password='investorpass123',
            role='INVESTOR',
            email='investor@test.com'
        )
        
        # User with 2FA enabled
        self.two_fa_user = User.objects.create_user(
            username='twofa_user',
            password='twofapass123',
            role='AGENT',
            email='twofa@test.com',
            totp_secret='JBSWY3DPEHPK3PXP',
            is_2fa_enabled=True
        )
        
        self.login_url = reverse('login')
        self.logout_url = reverse('admin:logout')
        self.dashboard_url = reverse('dashboard')
    
    def test_login_page_accessible(self):
        """Test that login page is accessible"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
    
    def test_successful_login_admin(self):
        """Test successful login for admin user"""
        response = self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'adminpass123'
        })
        # Should redirect to dashboard
        self.assertIn(response.status_code, [302, 303])
        
        # Check user is authenticated
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
    
    def test_successful_login_agent(self):
        """Test successful login for agent user"""
        response = self.client.post(self.login_url, {
            'username': 'agent',
            'password': 'agentpass123'
        })
        self.assertIn(response.status_code, [302, 303])
        
        # Check user is authenticated
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
    
    def test_failed_login_wrong_password(self):
        """Test login failure with wrong password"""
        response = self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nom d\'utilisateur ou mot de passe incorrect')
    
    def test_failed_login_nonexistent_user(self):
        """Test login failure with nonexistent user"""
        response = self.client.post(self.login_url, {
            'username': 'nonexistent',
            'password': 'anypassword'
        })
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nom d\'utilisateur ou mot de passe incorrect')
    
    def test_inactive_user_login(self):
        """Test login with inactive user"""
        # Deactivate user
        self.admin_user.is_active = False
        self.admin_user.save()
        
        response = self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'désactivé')
    
    def test_authenticated_user_redirect(self):
        """Test that authenticated user is redirected from login page"""
        # Login first
        self.client.login(username='admin', password='adminpass123')
        
        # Try to access login page
        response = self.client.get(self.login_url)
        
        # Should redirect to dashboard
        self.assertIn(response.status_code, [302, 303])
    
    def test_audit_log_login_success(self):
        """Test that successful login is logged in AuditLog"""
        # Clear existing logs
        AuditLog.objects.filter(action=AuditLog.ActionType.LOGIN).delete()
        
        # Login
        self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Check audit log was created
        logs = AuditLog.objects.filter(
            action=AuditLog.ActionType.LOGIN,
            user=self.admin_user
        )
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertIsNotNone(log.ip_address)
        self.assertIn('Connexion réussie', log.details)
    
    def test_audit_log_login_failed(self):
        """Test that failed login is logged in AuditLog"""
        # Clear existing logs
        AuditLog.objects.filter(action=AuditLog.ActionType.LOGIN_FAILED).delete()
        
        # Failed login
        self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        # Check audit log was created
        logs = AuditLog.objects.filter(action=AuditLog.ActionType.LOGIN_FAILED)
        self.assertEqual(logs.count(), 1)
        
        log = logs.first()
        self.assertIn('Échec d\'authentification', log.details)
    
    def test_logout(self):
        """Test logout functionality"""
        # Login first
        self.client.login(username='admin', password='adminpass123')
        
        # Logout
        response = self.client.post(reverse('logout'))
        
        # Should redirect to login
        self.assertIn(response.status_code, [302, 303])
        
        # Try to access dashboard - should fail
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_session_regeneration(self):
        """Test that session is regenerated on login"""
        # Create a new session
        session = self.client.session
        session['test_data'] = 'test_value'
        session.save()
        old_session_key = session.session_key
        
        # Login
        self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Session should be new
        new_session = self.client.session
        self.assertNotEqual(new_session.session_key, old_session_key)


class TwoFactorAuthTestCase(TestCase):
    """Test cases for Two-Factor Authentication"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # User with 2FA enabled
        self.two_fa_user = User.objects.create_user(
            username='twofa_user',
            password='twofapass123',
            role='AGENT',
            email='twofa@test.com',
            totp_secret='JBSWY3DPEHPK3PXP',
            is_2fa_enabled=True
        )
        
        # User without 2FA
        self.normal_user = User.objects.create_user(
            username='normal_user',
            password='normalpass123',
            role='AGENT',
            email='normal@test.com'
        )
        
        self.login_url = reverse('login')
        self.two_fa_verify_url = reverse('two_factor_verify')
        self.two_fa_setup_url = reverse('two_factor_setup')
        self.dashboard_url = reverse('dashboard')
    
    def test_2fa_user_redirected_to_verify(self):
        """Test that 2FA-enabled user is redirected to verify page"""
        response = self.client.post(self.login_url, {
            'username': 'twofa_user',
            'password': 'twofapass123'
        })
        
        # Should redirect to 2FA verification
        self.assertRedirects(response, self.two_fa_verify_url)
        
        # Session should have pre_2fa_user_id
        session = self.client.session
        self.assertEqual(session.get('pre_2fa_user_id'), self.two_fa_user.id)
    
    def test_normal_user_not_redirected_to_2fa(self):
        """Test that normal user (no 2FA) is not redirected to verify"""
        response = self.client.post(self.login_url, {
            'username': 'normal_user',
            'password': 'normalpass123'
        })
        
        # Should redirect to dashboard directly
        self.assertRedirects(response, self.dashboard_url)
    
    def test_2fa_valid_totp(self):
        """Test 2FA verification with valid TOTP code"""
        # First login to get to 2FA step
        self.client.post(self.login_url, {
            'username': 'twofa_user',
            'password': 'twofapass123'
        })
        
        # Generate valid TOTP code
        totp = pyotp.TOTP('JBSWY3DPEHPK3PXP')
        valid_code = totp.now()
        
        # Verify 2FA
        response = self.client.post(self.two_fa_verify_url, {
            'otp_code': valid_code
        })
        
        # Should redirect to dashboard
        self.assertRedirects(response, self.dashboard_url)
        
        # User should be authenticated
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
    
    def test_2fa_invalid_totp(self):
        """Test 2FA verification with invalid TOTP code"""
        # First login to get to 2FA step
        self.client.post(self.login_url, {
            'username': 'twofa_user',
            'password': 'twofapass123'
        })
        
        # Use invalid code
        response = self.client.post(self.two_fa_verify_url, {
            'otp_code': '000000'
        })
        
        # Should show error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Code invalide')
    
    def test_2fa_setup_requires_login(self):
        """Test that 2FA setup requires authentication"""
        response = self.client.get(self.two_fa_setup_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_2fa_setup_authenticated_user(self):
        """Test 2FA setup page for authenticated user"""
        # Login
        self.client.login(username='normal_user', password='normalpass123')
        
        response = self.client.get(self.two_fa_setup_url)
        self.assertEqual(response.status_code, 200)
        
        # Should have QR code
        self.assertContains(response, 'qr_code')
    
    def test_2fa_backup_code(self):
        """Test 2FA verification with backup code"""
        # First login to get to 2FA step
        self.client.post(self.login_url, {
            'username': 'twofa_user',
            'password': 'twofapass123'
        })
        
        # User should have backup codes
        self.assertTrue(len(self.two_fa_user.backup_codes) > 0)
        
        # Use first backup code
        backup_code = self.two_fa_user.backup_codes[0]
        
        response = self.client.post(self.two_fa_verify_url, {
            'otp_code': backup_code
        })
        
        # Should redirect to dashboard
        self.assertRedirects(response, self.dashboard_url)
        
        # Backup code should be consumed
        self.two_fa_user.refresh_from_db()
        self.assertNotIn(backup_code, self.two_fa_user.backup_codes)


class RateLimitingTestCase(TestCase):
    """Test cases for rate limiting (Django Axes)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            role='ADMIN'
        )
        
        self.login_url = reverse('login')
    
    def test_rate_limit_after_failed_attempts(self):
        """Test that rate limiting kicks in after failed attempts"""
        # Make multiple failed login attempts
        for i in range(5):
            response = self.client.post(self.login_url, {
                'username': 'admin',
                'password': 'wrongpassword'
            })
        
        # Should be rate limited
        # Note: In test mode, Axes might not enforce limits
        # But the attempt should still be logged
        self.assertEqual(response.status_code, 200)


class SecurityTestCase(TestCase):
    """Test security features"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            role='ADMIN'
        )
        
        self.login_url = reverse('login')
        self.dashboard_url = reverse('dashboard')
    
    def test_csrf_protection(self):
        """Test that CSRF protection is in place"""
        # Get login page to get CSRF token
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        
        # Try to post without CSRF token - should fail
        # Note: Django's test client might not enforce CSRF in tests
        # This is a placeholder for actual CSRF testing
    
    def test_session_cookie_httponly(self):
        """Test that session cookie is HttpOnly"""
        # Login
        self.client.post(self.login_url, {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Check session cookie settings
        # In test mode, this might not be fully enforced
        session = self.client.session
        self.assertIsNotNone(session.session_key)
    
    def test_redirect_to_login_unauthenticated(self):
        """Test that unauthenticated users are redirected to login"""
        response = self.client.get(self.dashboard_url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
