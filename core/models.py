from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        AGENT = 'AGENT', 'Agent'
        ASSOCIATE = 'ASSOCIATE', 'Associé'
        INVESTOR = 'INVESTOR', 'Investisseur'

    role = models.CharField(
        "Rôle",
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN
    )
    phone = models.CharField("Téléphone", max_length=20, blank=True, null=True)
    profile_picture = models.ImageField("Photo de profil", upload_to='profile_pics/', blank=True, null=True)
    commission_rate = models.DecimalField(
        "Taux de commission (%)", 
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Pourcentage des frais générés reversé à l'agent"
    )
    is_active = models.BooleanField("Actif", default=True)
    
    # Two-Factor Authentication fields
    totp_secret = models.CharField(
        "Secret TOTP",
        max_length=32,
        blank=True,
        null=True,
        help_text="Secret pour l'authentification à deux facteurs"
    )
    is_2fa_enabled = models.BooleanField(
        "2FA activé",
        default=False,
        help_text="L'authentification à deux facteurs est-elle activée"
    )
    backup_codes = models.JSONField(
        "Codes de secours",
        blank=True,
        default=list,
        help_text="Codes de secours pour la récupération de compte"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def generate_totp_secret(self):
        """Generate a new TOTP secret for the user"""
        import secrets
        self.totp_secret = secrets.token_hex(16)
        return self.totp_secret
    
    def generate_backup_codes(self):
        """Generate backup codes for 2FA recovery"""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        self.backup_codes = codes
        return codes
    
    def verify_totp(self, code):
        """Verify a TOTP code"""
        import pyotp
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        code = code.upper()
        if code in self.backup_codes:
            self.backup_codes.remove(code)
            self.save(update_fields=['backup_codes'])
            return True
        return False


class Currency(models.Model):
    code = models.CharField("Code (e.g. USD)", max_length=3, unique=True)
    name = models.CharField("Nom", max_length=50)
    symbol = models.CharField("Symbole", max_length=10, blank=True)
    is_reference = models.BooleanField("Devise de référence", default=False)

    class Meta:
        verbose_name = "Devise"
        verbose_name_plural = "Devises"

    def __str__(self):
        return f"{self.code} - {self.name}"


class ExchangeRate(models.Model):
    base_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='base_rates', verbose_name="Devise source")
    target_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='target_rates', verbose_name="Devise cible")
    rate = models.DecimalField("Taux", max_digits=20, decimal_places=10)
    date_updated = models.DateTimeField("Dernière mise à jour", auto_now=True)

    class Meta:
        verbose_name = "Taux de change"
        verbose_name_plural = "Taux de change"

    def __str__(self):
        return f"1 {self.base_currency.code} = {self.rate} {self.target_currency.code}"


class AuditLog(models.Model):
    """Audit log for tracking all operations and changes"""
    
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', 'Création'
        UPDATE = 'UPDATE', 'Modification'
        DELETE = 'DELETE', 'Suppression'
        LOGIN = 'LOGIN', 'Connexion'
        LOGOUT = 'LOGOUT', 'Déconnexion'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Échec connexion'
        TRANSACTION = 'TRANSACTION', 'Transaction'
        EXPENSE = 'EXPENSE', 'Dépense'
        FEE_GRID = 'FEE_GRID', 'Grille de frais'
        CURRENCY = 'CURRENCY', 'Devise'
        EXCHANGE_RATE = 'EXCHANGE_RATE', 'Taux de change'
    
    action = models.CharField("Action", max_length=20, choices=ActionType.choices)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs',
        verbose_name="Utilisateur"
    )
    model_name = models.CharField("Modèle", max_length=100)
    object_id = models.CharField("ID de l'objet", max_length=50, blank=True, null=True)
    object_repr = models.CharField("Représentation de l'objet", max_length=200, blank=True)
    changes = models.JSONField("Modifications", blank=True, default=dict)
    ip_address = models.GenericIPAddressField("Adresse IP", blank=True, null=True)
    user_agent = models.TextField("User Agent", blank=True)
    timestamp = models.DateTimeField("Date/Heure", auto_now_add=True)
    
    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.model_name} - {self.user} - {self.timestamp}"
    
    @classmethod
    def log_create(cls, user, instance, created=True):
        """Log object creation"""
        action = cls.ActionType.CREATE if created else cls.ActionType.UPDATE
        changes = {}
        if created:
            for field in instance._meta.fields:
                value = getattr(instance, field.name, None)
                if value is not None and not field.primary_key:
                    changes[field.name] = [None, str(value)]
        
        cls.objects.create(
            action=action,
            user=user,
            model_name=instance._meta.model_name,
            object_id=str(instance.pk),
            object_repr=str(instance),
            changes=changes,
        )
    
    @classmethod
    def log_update(cls, user, instance, old_data, new_data):
        """Log object update"""
        changes = {}
        for field_name in set(old_data.keys()) | set(new_data.keys()):
            old_val = old_data.get(field_name)
            new_val = new_data.get(field_name)
            if old_val != new_val:
                changes[field_name] = [old_val, new_val]
        
        if changes:
            cls.objects.create(
                action=cls.ActionType.UPDATE,
                user=user,
                model_name=instance._meta.model_name,
                object_id=str(instance.pk),
                object_repr=str(instance),
                changes=changes,
            )
    
    @classmethod
    def log_delete(cls, user, instance):
        """Log object deletion"""
        cls.objects.create(
            action=cls.ActionType.DELETE,
            user=user,
            model_name=instance._meta.model_name,
            object_id=str(instance.pk),
            object_repr=str(instance),
            changes={},
        )
    
    @classmethod
    def log_action(cls, user, action, model_name, object_id=None, object_repr=None, changes=None, ip_address=None, user_agent=None):
        """Generic log method"""
        return cls.objects.create(
            action=action,
            user=user,
            model_name=model_name,
            object_id=str(object_id) if object_id else None,
            object_repr=str(object_repr) if object_repr else None,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )


class PayPeriod(models.Model):
    """
    Période de paie mensuelle pour le calcul des salaires
    """
    STATUS_CHOICES = [
        ('OPEN', 'Ouvert'),
        ('CLOSED', 'Clôturé'),
        ('PAID', 'Payé'),
    ]
    
    month = models.PositiveSmallIntegerField("Mois", validators=[
        MinValueValidator(1), MaxValueValidator(12)
    ])
    year = models.PositiveIntegerField("Année")
    start_date = models.DateField("Date de début")
    end_date = models.DateField("Date de fin")
    status = models.CharField("Statut", max_length=20, choices=STATUS_CHOICES, default='OPEN')
    
    # Paramètres définis par l'admin
    reserve_percentage = models.DecimalField(
        "Pourcentage de réserve (%)", 
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        help_text="Pourcentage des revenus mis en réserve avant calcul des bénéfices"
    )
    payment_date = models.DateField(
        "Date de paie prévue", 
        null=True, 
        blank=True,
        help_text="Date à laquelle les salaires seront payés"
    )
    
    # Calculs automatiques
    total_fees = models.DecimalField("Total des frais", max_digits=20, decimal_places=2, default=0)
    total_expenses = models.DecimalField("Total des dépenses", max_digits=20, decimal_places=2, default=0)
    reserve_amount = models.DecimalField("Montant réservé", max_digits=20, decimal_places=2, default=0)
    net_profit = models.DecimalField("Bénéfice net", max_digits=20, decimal_places=2, default=0)
    total_salaries = models.DecimalField("Total des salaires", max_digits=20, decimal_places=2, default=0)
    
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)
    
    class Meta:
        verbose_name = "Période de paie"
        verbose_name_plural = "Périodes de paie"
        unique_together = ['month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.month:02d}/{self.year} - {self.get_status_display()}"
    
    def clean(self):
        if self.payment_date and self.payment_date <= self.end_date:
            from django.core.exceptions import ValidationError
            raise ValidationError("La date de paie doit être après la fin de la période")
    
    def calculate_financials(self):
        """
        Calcule automatiquement les données financières de la période
        """
        from operations.models import Operation
        from finance.models import Expense
        
        # Calculer le total des frais générés
        operations = Operation.objects.filter(
            date_time__date__gte=self.start_date,
            date_time__date__lte=self.end_date
        )
        self.total_fees = operations.aggregate(
            total=models.Sum('fee_calculated')
        )['total'] or Decimal('0')
        
        # Calculer le total des dépenses
        self.total_expenses = Expense.objects.filter(
            date__gte=self.start_date,
            date__lte=self.end_date
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        
        # Calculer le montant réservé
        self.reserve_amount = self.total_fees * (self.reserve_percentage / 100)
        
        # Calculer le bénéfice net
        self.net_profit = self.total_fees - self.total_expenses - self.reserve_amount
        
        self.save()
        return self.net_profit
    
    def get_salaries_total(self):
        """
        Retourne le total des salaires calculés
        """
        return self.monthly_salaries.aggregate(
            total=models.Sum('total_salary')
        )['total'] or Decimal('0')
    
    def is_payment_due(self):
        """
        Vérifie si la date de paie est arrivée
        """
        if not self.payment_date:
            return False
        return timezone.now().date() >= self.payment_date
    
    def days_until_payment(self):
        """
        Retourne le nombre de jours avant la paie
        """
        if not self.payment_date:
            return None
        delta = self.payment_date - timezone.now().date()
        return delta.days if delta.days > 0 else 0


class MonthlySalary(models.Model):
    """
    Salaire mensuel d'un agent pour une période donnée
    """
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('PAID', 'Payé'),
        ('PARTIAL', 'Partiellement payé'),
    ]
    
    pay_period = models.ForeignKey(
        PayPeriod, 
        on_delete=models.PROTECT, 
        verbose_name="Période de paie",
        related_name='monthly_salaries'
    )
    agent = models.ForeignKey(
        'User', 
        on_delete=models.PROTECT, 
        verbose_name="Agent",
        limit_choices_to={'role': 'AGENT'}
    )
    
    commission_percentage = models.DecimalField(
        "Pourcentage de commission (%)", 
        max_digits=5, 
        decimal_places=2,
        help_text="Pourcentage des bénéfices alloué à cet agent"
    )
    
    # Calculs salariaux
    base_salary = models.DecimalField(
        "Salaire de base", 
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Calculé automatiquement: Bénéfices × Pourcentage"
    )
    bonus_amount = models.DecimalField(
        "Bonus", 
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Bonus manuel défini par l'administrateur"
    )
    total_salary = models.DecimalField(
        "Salaire total", 
        max_digits=20, 
        decimal_places=2, 
        default=0,
        help_text="Salaire de base + Bonus"
    )
    paid_amount = models.DecimalField(
        "Montant payé", 
        max_digits=20, 
        decimal_places=2, 
        default=0
    )
    paid_date = models.DateTimeField(
        "Date de paiement", 
        null=True, 
        blank=True
    )
    status = models.CharField(
        "Statut", 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    
    # Notes et suivi
    payment_notes = models.TextField(
        "Notes de paiement", 
        blank=True,
        help_text="Notes sur le paiement (ex: payé en espèces)"
    )
    
    created_at = models.DateTimeField("Créé le", auto_now_add=True)
    updated_at = models.DateTimeField("Mis à jour le", auto_now=True)
    
    class Meta:
        verbose_name = "Salaire mensuel"
        verbose_name_plural = "Salaires mensuels"
        unique_together = ['pay_period', 'agent']
        ordering = ['-pay_period__year', '-pay_period__month', 'agent__username']
    
    def __str__(self):
        return f"{self.agent.username} - {self.pay_period.month:02d}/{self.pay_period.year}"
    
    def calculate_salary(self):
        """
        Calcule automatiquement le salaire basé sur les bénéfices
        """
        if self.pay_period.net_profit > 0:
            self.base_salary = self.pay_period.net_profit * (self.commission_percentage / 100)
        else:
            self.base_salary = Decimal('0')
        
        self.total_salary = self.base_salary + self.bonus_amount
        self.save()
        return self.total_salary
    
    def get_remaining_amount(self):
        """
        Retourne le montant restant à payer
        """
        return self.total_salary - self.paid_amount
    
    def is_fully_paid(self):
        """
        Vérifie si le salaire est complètement payé
        """
        return self.paid_amount >= self.total_salary
    
    def mark_as_paid(self, payment_amount=None, notes=""):
        """
        Marque le salaire comme payé
        """
        if payment_amount:
            self.paid_amount = payment_amount
        else:
            self.paid_amount = self.total_salary
        
        self.paid_date = timezone.now()
        self.payment_notes = notes
        self.status = 'PAID'
        self.save()
    
    def mark_partial_payment(self, payment_amount, notes=""):
        """
        Enregistre un paiement partiel
        """
        self.paid_amount += payment_amount
        self.payment_notes = f"{self.payment_notes}\n{notes}".strip()
        
        if self.paid_amount >= self.total_salary:
            self.status = 'PAID'
            self.paid_date = timezone.now()
        else:
            self.status = 'PARTIAL'
        
        self.save()
