from django.shortcuts import redirect, render
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
import logging
import pyotp
import qrcode
import io
import base64

# Get logger for security events
logger = logging.getLogger(__name__)


def custom_login(request):
    """
    Vue de connexion personnalisée avec redirection par rôle et logging de sécurité
    """
    # Si déjà connecté, rediriger vers le dashboard approprié
    if request.user.is_authenticated:
        return redirect_to_user_dashboard(request.user)
    
    error = None
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Get client IP for logging
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Authentifier l'utilisateur
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                # Check if 2FA is enabled
                if user.is_2fa_enabled:
                    # Store user ID in session and require 2FA
                    request.session['pre_2fa_user_id'] = user.id
                    request.session['2fa_step'] = 'verify'
                    return redirect('two_factor_verify')
                else:
                    # === SUCCESSFUL LOGIN WITHOUT 2FA ===
                    
                    # Regenerate session to prevent session fixation
                    request.session.flush()
                    
                    # Connexion réussie
                    login(request, user)
                    
                    # Log successful login
                    try:
                        from core.models import AuditLog
                        AuditLog.objects.create(
                            action=AuditLog.ActionType.LOGIN,
                            user=user,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            changes={"message": f"Connexion réussie - Rôle: {user.role}"}
                        )
                    except Exception as e:
                        logger.error(f"Failed to log successful login: {e}")
                    
                    # Rediriger vers le next参数 ou le dashboard
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect_to_user_dashboard(user)
            else:
                # === INACTIVE ACCOUNT ===
                error = "Ce compte est désactivé. Veuillez contacter l'administrateur."
                
                # Log failed login attempt (inactive account)
                try:
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        action=AuditLog.ActionType.LOGIN_FAILED,
                        user=None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        changes={"message": f"Compte désactivé - Username: {username}"}
                    )
                except Exception as e:
                    logger.error(f"Failed to log failed login: {e}")
        else:
            # === FAILED LOGIN ATTEMPT ===
            error = "Nom d'utilisateur ou mot de passe incorrect."
            
            # Log failed login attempt
            try:
                from core.models import AuditLog
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN_FAILED,
                    user=None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    changes={"message": f"Échec d'authentification - Username: {username}"}
                )
            except Exception as e:
                logger.error(f"Failed to log failed login: {e}")
    
    return render(request, 'registration/login.html', {'error': error})


def two_factor_verify(request):
    """
    Vue de vérification 2FA après login
    """
    # Check if user is in pre-2fa state
    user_id = request.session.get('pre_2fa_user_id')
    if not user_id:
        # No pending 2FA, redirect to login
        return redirect('login')
    
    from core.models import User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Session expirée. Veuillez vous reconnecter.")
        return redirect('login')
    
    error = None
    
    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip()
        
        # Try TOTP first
        if user.verify_totp(code):
            # === SUCCESSFUL 2FA VERIFICATION ===
            
            # Regenerate session to prevent session fixation
            request.session.flush()
            
            # Log the user in
            login(request, user)
            
            # Log successful 2FA login
            try:
                from core.models import AuditLog
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    changes={"message": f"Connexion réussie avec 2FA - Rôle: {user.role}"}
                )
            except Exception as e:
                logger.error(f"Failed to log 2FA login: {e}")
            
            return redirect_to_user_dashboard(user)
        
        # Try backup code
        elif user.verify_backup_code(code):
            # === SUCCESSFUL BACKUP CODE VERIFICATION ===
            
            # Regenerate session
            request.session.flush()
            
            # Log the user in
            login(request, user)
            
            # Notify user about backup code usage
            messages.warning(request, "Code de secours utilisé. Générez de nouveaux codes dans votre profil.")
            
            # Log successful backup code login
            try:
                from core.models import AuditLog
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    changes={"message": f"Connexion par code de secours - Rôle: {user.role}"}
                )
            except Exception as e:
                logger.error(f"Failed to log backup code login: {e}")
            
            return redirect_to_user_dashboard(user)
        
        else:
            # === FAILED 2FA VERIFICATION ===
            error = "Code invalide. Veuillez réessayer."
            
            # Log failed 2FA attempt
            try:
                from core.models import AuditLog
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                AuditLog.objects.create(
                    action=AuditLog.ActionType.LOGIN_FAILED,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    changes={"message": f"Échec vérification 2FA"}
                )
            except Exception as e:
                logger.error(f"Failed to log failed 2FA: {e}")
    
    return render(request, 'registration/two_factor_verify.html', {
        'error': error,
        'username': user.username
    })


@login_required
def two_factor_setup(request):
    """
    Vue de configuration 2FA pour les utilisateurs
    """
    user = request.user
    
    # Generate new TOTP secret if not exists
    if not user.totp_secret:
        user.generate_totp_secret()
        user.generate_backup_codes()
        user.save()
    
    # Generate QR code
    totp = pyotp.TOTP(user.totp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.username,
        issuer_name="Rapid Cash"
    )
    
    # Generate QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'qr_code': f"data:image/png;base64,{qr_code_base64}",
        'totp_secret': user.totp_secret,
        'backup_codes': user.backup_codes,
    }
    
    return render(request, 'registration/two_factor_setup.html', context)


@login_required
@require_http_methods(["POST"])
def two_factor_enable(request):
    """
    Activer 2FA après vérification du code
    """
    code = request.POST.get('otp_code', '').strip()
    user = request.user
    
    if user.verify_totp(code):
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])
        
        # Regenerate backup codes after enabling
        user.generate_backup_codes()
        user.save(update_fields=['backup_codes'])
        
        messages.success(request, "L'authentification à deux facteurs est maintenant activée!")
        
        # Log 2FA enablement
        try:
            from core.models import AuditLog
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            AuditLog.objects.create(
                action=AuditLog.ActionType.UPDATE,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                changes={"message": "Activation de l'authentification à deux facteurs"}
            )
        except Exception as e:
            logger.error(f"Failed to log 2FA enable: {e}")
    else:
        messages.error(request, "Code invalide. L'activation a échoué.")
    
    return redirect('two_factor_setup')


@login_required
@require_http_methods(["POST"])
def two_factor_disable(request):
    """
    Désactiver 2FA (avec vérification)
    """
    code = request.POST.get('otp_code', '').strip()
    user = request.user
    
    if user.verify_totp(code) or user.verify_backup_code(code):
        user.is_2fa_enabled = False
        user.totp_secret = None
        user.backup_codes = []
        user.save(update_fields=['is_2fa_enabled', 'totp_secret', 'backup_codes'])
        
        messages.success(request, "L'authentification à deux facteurs a été désactivée.")
        
        # Log 2FA disable
        try:
            from core.models import AuditLog
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            AuditLog.objects.create(
                action=AuditLog.ActionType.UPDATE,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                changes={"message": "Désactivation de l'authentification à deux facteurs"}
            )
        except Exception as e:
            logger.error(f"Failed to log 2FA disable: {e}")
    else:
        messages.error(request, "Code invalide. La désactivation a échoué.")
    
    return redirect('core:user_profile')


def redirect_to_user_dashboard(user):
    """
    Redirige l'utilisateur vers le dashboard approprié selon son rôle
    """
    # Map roles to their respective dashboard views
    role_dashboards = {
        'ADMIN': 'dashboard',
        'AGENT': 'dashboard_agent',  # Create this view for agents
        'ASSOCIATE': 'dashboard_associate',  # Create this view for associates
        'INVESTOR': 'dashboard_investor',  # Create this view for investors
    }
    
    dashboard_name = role_dashboards.get(user.role, 'dashboard')
    
    # For now, all roles go to main dashboard but with different contexts
    # In production, create separate dashboard views per role
    return redirect('dashboard')


@require_http_methods(["POST"])
@login_required
def custom_logout(request):
    """
    Vue de logout personnalisée avec logging approprié
    """
    # Get user info before logout for logging
    user = request.user
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Enregistrer l'action de logout dans l'audit
    try:
        from core.models import AuditLog
        AuditLog.objects.create(
            action=AuditLog.ActionType.LOGOUT,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            changes={"message": "Déconnexion de l'utilisateur"}
        )
    except Exception as e:
        # Log the error instead of silently ignoring
        logger.error(f"Failed to create logout audit log: {e}")
    
    # Effectuer le logout
    logout(request)
    
    # Message de succès
    messages.success(request, "Vous avez été déconnecté avec succès.")
    
    # Redirection vers la page de login
    return redirect('login')
