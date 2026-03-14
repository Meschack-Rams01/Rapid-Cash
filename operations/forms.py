from django import forms
from .models import Operation, Caisse
from core.models import Currency

class CaisseForm(forms.ModelForm):
    class Meta:
        model = Caisse
        fields = ['name', 'currency', 'agent']
        labels = {
            'name': 'Nom de la caisse',
            'currency': 'Devise par défaut',
            'agent': 'Agent assigné'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-dark', 'placeholder': 'Ex: Caisse Principale'}),
            'currency': forms.Select(attrs={'class': 'input-dark'}),
            'agent': forms.Select(attrs={'class': 'input-dark'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['agent'].required = False
        self.fields['agent'].empty_label = "--- Aucune assignation (Optionnel) ---"

class OperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = [
            'type', 
            'amount_orig', 
            'currency_orig', 
            'observation'
        ]
        labels = {
            'type': "Type d'Opération",
            'amount_orig': "Montant",
            'currency_orig': "Devise",
            'observation': "Commentaire"
        }
        widgets = {
            'type': forms.Select(attrs={'class': 'input-dark'}),
            'amount_orig': forms.NumberInput(attrs={'class': 'input-dark', 'placeholder': '0.00', 'step': '0.01', 'x-model': 'amount', ':class': '!isAmountValid && amount > 0 ? \'!border-accent-danger\' : \'\' '}),
            'currency_orig': forms.Select(attrs={'class': 'input-dark', 'x-model': 'caisseCurrency'}),
            'observation': forms.Textarea(attrs={'class': 'input-dark', 'rows': 2, 'x-on:input': 'step = 4'}),
        }

    def __init__(self, *args, **kwargs):
        agent = kwargs.pop('agent', None)
        super().__init__(*args, **kwargs)
        
        # Store agent for caisse assignment
        self.agent = agent
        
        # Add custom validation
        self.fields['amount_orig'].validators.append(self.validate_amount)
    
    def validate_amount(self, value):
        if value <= 0:
            raise forms.ValidationError("Le montant doit être supérieur à 0")
        return value
    
    def get_agent_caisse(self):
        """Get the agent's assigned caisse"""
        if self.agent:
            if self.agent.role == 'ADMIN':
                # Pour les admins, prendre la première caisse disponible
                return Caisse.objects.first()
            else:
                # Pour les agents, prendre leur caisse assignée
                return Caisse.objects.filter(agent=self.agent).first()
        return None
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount_orig')
        op_type = cleaned_data.get('type')
        currency = cleaned_data.get('currency_orig')
        
        # Get agent's caisse
        agent_caisse = self.get_agent_caisse()
        if not agent_caisse:
            raise forms.ValidationError("Aucune caisse assignée à cet agent. Veuillez contacter l'administrateur.")
        
        # Store caisse for the operation
        self.instance.caisse = agent_caisse
        
        # Check currency match - if different, we need to convert
        if agent_caisse.currency != currency:
            # Try to convert the amount to caisse currency
            from decimal import Decimal
            from core.models import ExchangeRate
            try:
                # Look for direct rate: selected currency -> caisse currency
                rate_obj = ExchangeRate.objects.filter(
                    base_currency=currency,
                    target_currency=agent_caisse.currency
                ).first()
                
                if rate_obj:
                    # Convert amount
                    rate_decimal = Decimal(str(rate_obj.rate))
                    converted_amount = amount * rate_decimal
                    # Store conversion info for the view to use
                    self.converted_amount = converted_amount
                    self.converted_currency = agent_caisse.currency
                    self.exchange_rate_used = rate_decimal
                    self.add_error(None, f"Conversion automatique: {amount} {currency.code} = {converted_amount:.2f} {agent_caisse.currency.code} (taux: {rate_decimal})")
                else:
                    # Try inverse rate
                    inverse_rate_obj = ExchangeRate.objects.filter(
                        base_currency=agent_caisse.currency,
                        target_currency=currency
                    ).first()
                    
                    if inverse_rate_obj:
                        # Convert using inverse rate
                        rate_decimal = Decimal(str(inverse_rate_obj.rate))
                        converted_amount = amount / rate_decimal
                        self.converted_amount = converted_amount
                        self.converted_currency = agent_caisse.currency
                        self.exchange_rate_used = Decimal('1') / rate_decimal
                        self.add_error(None, f"Conversion automatique: {amount} {currency.code} = {converted_amount:.2f} {agent_caisse.currency.code} (taux: {self.exchange_rate_used:.6f})")
                    else:
                        raise forms.ValidationError(
                            f"Pas de taux de change trouvé entre {currency.code} et {agent_caisse.currency.code}. "
                            f"Veuillez configurer le taux dans Gestion > Taux de Change."
                        )
            except Exception as e:
                raise forms.ValidationError(f"Erreur de conversion: {str(e)}")
        
        # Check balance (using converted amount if applicable)
        check_amount = getattr(self, 'converted_amount', amount)
        
        if op_type == 'WITHDRAWAL' and check_amount:
            # Calculate fee for withdrawal (in caisse currency)
            from .services import OperationService
            fee = OperationService._calculate_fee(check_amount, agent_caisse.currency)
            required_amount = check_amount + fee
            
            if agent_caisse.balance < required_amount:
                raise forms.ValidationError(f"Fonds insuffisants. Solde disponible: {agent_caisse.balance} {agent_caisse.currency.code}, Requis: {required_amount:.2f} {agent_caisse.currency.code}")
        elif op_type == 'TRANSFER' and check_amount:
            if agent_caisse.balance < check_amount:
                raise forms.ValidationError(f"Fonds insuffisants. Solde disponible: {agent_caisse.balance} {agent_caisse.currency.code}, Requis: {check_amount:.2f} {agent_caisse.currency.code}")
        
        return cleaned_data
