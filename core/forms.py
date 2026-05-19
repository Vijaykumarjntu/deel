# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Company, Contractor

class CompanySignupForm(UserCreationForm):
    company_name = forms.CharField(max_length=255, label='Company Name')
    website = forms.URLField(required=False, label='Website (optional)')
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('email', 'company_name', 'website', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Use email as username
        user.role = 'company'
        if commit:
            user.save()
            Company.objects.create(
                user=user,
                name=self.cleaned_data['company_name'],
                website=self.cleaned_data.get('website', '')
            )
        return user

class ContractorForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    full_name = forms.CharField(max_length=255)
    
    class Meta:
        model = Contractor
        fields = ['full_name', 'country', 'tax_id', 'bank_account_name', 'bank_iban_or_account']
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        # Create User for contractor
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            role='contractor'
        )
        
        contractor = super().save(commit=False)
        contractor.user = user
        contractor.company = self.company
        contractor.full_name = self.cleaned_data['full_name']
        
        if commit:
            contractor.save()
        return contractor