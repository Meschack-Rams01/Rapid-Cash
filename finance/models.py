from django.db import models
from django.conf import settings
from core.models import Currency

class Expense(models.Model):
    date = models.DateField("Date", auto_now_add=True)
    amount = models.DecimalField("Montant", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    reason = models.CharField("Motif", max_length=255)
    category = models.CharField("Catégorie", max_length=100, blank=True)
    destination = models.CharField("Destination", max_length=100, blank=True)
    comment = models.TextField("Commentaire", blank=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Administrateur")

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"

    def __str__(self):
        return f"{self.date} - {self.reason} ({self.amount} {self.currency.code})"

class PartnerContract(models.Model):
    class Type(models.TextChoices):
        ASSOCIATE = 'ASSOCIATE', 'Associé'
        INVESTOR = 'INVESTOR', 'Investisseur'
    
    partner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contract', verbose_name="Partenaire")
    type = models.CharField("Type de contrat", max_length=20, choices=Type.choices)
    amount_engaged = models.DecimalField("Montant engagé", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    start_date = models.DateField("Date de début")
    duration_months = models.IntegerField("Durée (mois)", null=True, blank=True)
    expected_return_percent = models.DecimalField("Retour attendu (%)", max_digits=5, decimal_places=2)
    status = models.CharField("Statut", max_length=20, default='ACTIVE')

    class Meta:
        verbose_name = "Contrat Partenaire"
        verbose_name_plural = "Contrats Partenaires"

    def __str__(self):
        return f"Contrat {self.get_type_display()} - {self.partner.username}"
    
    @property
    def progress(self):
        """Calculate progress based on payments received"""
        from django.db.models import Sum
        total_paid = self.payments.aggregate(total=Sum('amount'))['total'] or 0
        if self.amount_engaged > 0:
            return min(100, (total_paid / self.amount_engaged) * 100)
        return 0

class PartnerPayment(models.Model):
    contract = models.ForeignKey(PartnerContract, on_delete=models.CASCADE, related_name='payments', verbose_name="Contrat lié")
    date = models.DateField("Date de paiement", auto_now_add=True)
    amount = models.DecimalField("Montant payé", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    note = models.TextField("Note", blank=True)

    class Meta:
        verbose_name = "Paiement Partenaire"
        verbose_name_plural = "Paiements Partenaires"

    def __str__(self):
        return f"Paiement {self.amount} {self.currency.code} à {self.contract.partner.username}"

class CapitalTransaction(models.Model):
    class Type(models.TextChoices):
        INJECTION = 'INJECTION', 'Injection de capital (Apport)'
        RETRAIT = 'RETRAIT', 'Retrait de capital'

    type = models.CharField("Type", max_length=20, choices=Type.choices)
    amount = models.DecimalField("Montant", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    date_time = models.DateTimeField("Date & Heure", auto_now_add=True)
    reason = models.CharField("Motif", max_length=255)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Administrateur", related_name="capital_transactions")
    
    class Meta:
        verbose_name = "Transaction sur Capital"
        verbose_name_plural = "Transactions sur Capital"
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} {self.currency.code} ({self.date_time.strftime('%Y-%m-%d')})"

class ProfitWithdrawal(models.Model):
    amount = models.DecimalField("Montant retiré", max_digits=20, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Devise")
    date_time = models.DateTimeField("Date & Heure", auto_now_add=True)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Administrateur", related_name="profit_withdrawals")
    note = models.TextField("Note", blank=True)

    class Meta:
        verbose_name = "Retrait de Bénéfice"
        verbose_name_plural = "Retraits de Bénéfices"
        indexes = [
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"Retrait Bénéfice - {self.amount} {self.currency.code} ({self.date_time.strftime('%Y-%m-%d')})"
