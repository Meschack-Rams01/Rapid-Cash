from django import forms
from .models import Expense, CapitalTransaction, ProfitWithdrawal
from core.models import Currency

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['amount', 'currency', 'reason', 'category', 'destination', 'comment']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'currency': forms.Select(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'reason': forms.TextInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'e.g. Loyer, Internet, Transport...'}),
            'category': forms.TextInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'placeholder': 'e.g. Logistique, RH, IT...'}),
            'destination': forms.TextInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'comment': forms.Textarea(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure currencies are loaded
        self.fields['currency'].queryset = Currency.objects.all()

class CapitalTransactionForm(forms.ModelForm):
    class Meta:
        model = CapitalTransaction
        fields = ['type', 'amount', 'currency', 'reason']
        labels = {
            'type': "Type d'opération",
            'amount': "Montant",
            'currency': "Devise",
            'reason': "Motif ou Description"
        }
        widgets = {
            'type': forms.Select(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'reason': forms.TextInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
        }
        
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à 0.")
        return amount

class ProfitWithdrawalForm(forms.ModelForm):
    class Meta:
        model = ProfitWithdrawal
        fields = ['amount', 'currency', 'note']
        labels = {
            'amount': "Montant à retirer",
            'currency': "Devise",
            'note': "Note ou Justificatif"
        }
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500'}),
            'note': forms.Textarea(attrs={'class': 'block w-full rounded-lg border-slate-200 text-sm focus:ring-brand-500 focus:border-brand-500', 'rows': 2}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à 0.")
        return amount
