from django.db import models
from django.conf import settings
from core.models import Currency

class FeeGrid(models.Model):
    """
    Grille de frais unique en USD (devise de référence).
    Les frais pour toutes les autres devises sont calculés par conversion.
    """
    min_amount = models.DecimalField("Montant Min (USD)", max_digits=20, decimal_places=2)
    max_amount = models.DecimalField("Montant Max (USD)", max_digits=20, decimal_places=2)
    fee_amount = models.DecimalField("Frais Fixe (USD)", max_digits=20, decimal_places=2)
    # Currency conservé pour compatibilité mais toujours USD
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name="Devise (toujours USD)", limit_choices_to={'code': 'USD'})

    class Meta:
        verbose_name = "Grille de Frais"
        verbose_name_plural = "Grilles de Frais"
        # Contrainte unique sur les tranches
        constraints = [
            models.UniqueConstraint(
                fields=['min_amount', 'max_amount'],
                name='unique_fee_range'
            )
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        # Forcer USD uniquement
        if self.currency and self.currency.code != 'USD':
            raise ValidationError("La grille de frais doit être définie uniquement en USD. Les autres devises utilisent la conversion automatique.")
        super().clean()

class Caisse(models.Model):
    name = models.CharField("Nom de la caisse", max_length=100)
    agent = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='caisse', verbose_name="Agent titulaire")
    balance = models.DecimalField("Solde actuel", max_digits=20, decimal_places=2, default=0)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise de la caisse")

    class Meta:
        verbose_name = "Caisse"
        verbose_name_plural = "Caisses"
        indexes = [
            models.Index(fields=['agent']),
            models.Index(fields=['currency']),
        ]

    def __str__(self):
        return f"Caisse {self.name} ({self.balance} {self.currency.code})"
    
    def clean(self):
        if self.balance < 0:
            from django.core.exceptions import ValidationError
            raise ValidationError("Caisse balance cannot be negative")

class Operation(models.Model):
    class Type(models.TextChoices):
        TRANSFER = 'TRANSFER', 'Transfert'
        WITHDRAWAL = 'WITHDRAWAL', 'Retrait'
    
    transaction_number = models.CharField("N° Transaction", max_length=50, unique=True)
    date_time = models.DateTimeField("Date & Heure", auto_now_add=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Agent responsable")
    caisse = models.ForeignKey(Caisse, on_delete=models.PROTECT, verbose_name="Caisse utilisée")
    type = models.CharField("Type d'opération", max_length=20, choices=Type.choices)
    
    amount_orig = models.DecimalField("Montant saisi", max_digits=20, decimal_places=2)
    currency_orig = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='operations_orig', verbose_name="Devise d'origine")
    
    amount_ref = models.DecimalField("Montant (REF USD)", max_digits=20, decimal_places=2)
    currency_ref = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='operations_ref', verbose_name="Devise de référence")
    
    exchange_rate = models.DecimalField("Taux utilisé", max_digits=20, decimal_places=10)
    fee_calculated = models.DecimalField("Frais appliqués", max_digits=20, decimal_places=2)
    
    observation = models.TextField("Commentaire", blank=True, null=True)
    status = models.CharField("Statut", max_length=20, default='COMPLETED')

    class Meta:
        verbose_name = "Opération"
        verbose_name_plural = "Opérations"
        indexes = [
            models.Index(fields=['agent', '-date_time']),
            models.Index(fields=['transaction_number']),
            models.Index(fields=['status']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.type} - {self.amount_orig} {self.currency_orig.code}"

class FondAllocation(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='allocations_donnees', verbose_name="Administrateur")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='allocations_recues', verbose_name="Agent", limit_choices_to={'role': 'AGENT'})
    amount = models.DecimalField("Montant", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    date_time = models.DateTimeField("Date & Heure", auto_now_add=True)
    note = models.TextField("Note", blank=True, help_text="Exemple : Fonds de démarrage Lundi")

    class Meta:
        verbose_name = "Allocation de fonds (Agent)"
        verbose_name_plural = "Allocations de fonds (Agents)"
        indexes = [
            models.Index(fields=['agent']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"Allocation: {self.amount} {self.currency.code} attribué à {self.agent.username}"
