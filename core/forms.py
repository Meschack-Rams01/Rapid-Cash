from django import forms
from django.contrib.auth import get_user_model
from finance.models import Currency, PartnerContract

User = get_user_model()

class UserProfileForm(forms.ModelForm):
    """Formulaire pour mettre à jour le profil utilisateur"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'profile_picture']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-dark'}),
            'last_name': forms.TextInput(attrs={'class': 'input-dark'}),
            'email': forms.EmailInput(attrs={'class': 'input-dark'}),
            'phone': forms.TextInput(attrs={'class': 'input-dark'}),
            'profile_picture': forms.FileInput(attrs={'class': 'input-dark', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'Prénom'
        self.fields['last_name'].label = 'Nom'
        self.fields['email'].label = 'Email'
        self.fields['phone'].label = 'Téléphone'
        self.fields['profile_picture'].label = 'Photo de profil'
        
        # Rendre le champ de photo optionnel
        self.fields['profile_picture'].required = False


class AgentCreationForm(forms.ModelForm):
    """Formulaire pour la création d'un Agent par l'Admin"""
    username = forms.CharField(max_length=150, label="Nom d'utilisateur", widget=forms.TextInput(attrs={'class': 'input-dark'}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'class': 'input-dark'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'input-dark'}), label="Mot de passe")
    first_name = forms.CharField(max_length=30, label="Prénom", widget=forms.TextInput(attrs={'class': 'input-dark'}))
    last_name = forms.CharField(max_length=30, label="Nom", widget=forms.TextInput(attrs={'class': 'input-dark'}))
    phone = forms.CharField(max_length=20, required=False, label="Téléphone", widget=forms.TextInput(attrs={'class': 'input-dark'}))
    commission_rate = forms.DecimalField(max_digits=5, decimal_places=2, required=False, label="Taux de commission (%)", widget=forms.NumberInput(attrs={'class': 'input-dark'}))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone', 'commission_rate']

    def save(self, commit=True):
        # Utilise create_user du modèle pour hacher le mot de passe
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data['phone'],
            role='AGENT',
            commission_rate=self.cleaned_data.get('commission_rate')
        )
        return user


class AgentEditForm(forms.ModelForm):
    """Formulaire pour l'édition d'un Agent par l'Admin"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'commission_rate', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input-dark'}),
            'last_name': forms.TextInput(attrs={'class': 'input-dark'}),
            'email': forms.EmailInput(attrs={'class': 'input-dark'}),
            'phone': forms.TextInput(attrs={'class': 'input-dark'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'input-dark'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-dark-border bg-dark-surface2 text-accent-primary focus:ring-accent-primary mr-2'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'Prénom'
        self.fields['last_name'].label = 'Nom'
        self.fields['email'].label = 'Email'
        self.fields['phone'].label = 'Téléphone'
        self.fields['commission_rate'].label = 'Taux de commission (%)'
        self.fields['is_active'].label = 'Compte Actif'

class AssociateForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label="Nom d'utilisateur")
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")
    first_name = forms.CharField(max_length=30, label="Prénom")
    last_name = forms.CharField(max_length=30, label="Nom")
    phone = forms.CharField(max_length=20, required=False, label="Téléphone")
    
    # Contract fields
    amount_engaged = forms.DecimalField(max_digits=20, decimal_places=2, label="Montant engagé")
    currency = forms.ModelChoiceField(queryset=Currency.objects.all(), label="Devise")
    duration_months = forms.IntegerField(required=False, label="Durée (mois)")
    expected_return_percent = forms.DecimalField(max_digits=5, decimal_places=2, label="Retour attendu (%)")
    
    class Meta:
        model = PartnerContract
        fields = ['amount_engaged', 'currency', 'duration_months', 'expected_return_percent']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.all()
    
    def save(self, commit=True):
        # Create user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data['phone'],
            role='ASSOCIATE'
        )
        
        # Create contract
        contract = super().save(commit=False)
        contract.partner = user
        contract.type = 'ASSOCIATE'
        if commit:
            contract.save()
        
        return contract

class InvestorForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label="Nom d'utilisateur")
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")
    first_name = forms.CharField(max_length=30, label="Prénom")
    last_name = forms.CharField(max_length=30, label="Nom")
    phone = forms.CharField(max_length=20, required=False, label="Téléphone")
    
    # Contract fields
    amount_engaged = forms.DecimalField(max_digits=20, decimal_places=2, label="Montant investi")
    currency = forms.ModelChoiceField(queryset=Currency.objects.all(), label="Devise")
    duration_months = forms.IntegerField(required=False, label="Durée (mois)")
    expected_return_percent = forms.DecimalField(max_digits=5, decimal_places=2, label="Retour attendu (%)")
    
    class Meta:
        model = PartnerContract
        fields = ['amount_engaged', 'currency', 'duration_months', 'expected_return_percent']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.all()
    
    def save(self, commit=True):
        # Create user first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data['phone'],
            role='INVESTOR'
        )
        
        # Create contract
        contract = super().save(commit=False)
        contract.partner = user
        contract.type = 'INVESTOR'
        if commit:
            contract.save()
        
        return contract
