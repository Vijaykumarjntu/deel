# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Company, Contractor
from payments.localization import LocalizationEngine  # ← ADD THIS IMPORT

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
    
    # Dynamic fields for each country
    # India specific
    pan = forms.CharField(max_length=10, required=False, label='PAN Card Number')
    aadhar = forms.CharField(max_length=12, required=False, label='Aadhaar Number')
    gstin = forms.CharField(max_length=15, required=False, label='GSTIN')
    
    # Brazil specific
    cpf = forms.CharField(max_length=11, required=False, label='CPF Number')
    rg = forms.CharField(max_length=9, required=False, label='RG (Identity Card)')
    pis_pasep = forms.CharField(max_length=11, required=False, label='PIS/PASEP')

    # Germany specific
    steuer_id = forms.CharField(max_length=11, required=False, label='Tax ID (Steuer ID)')
    ust_id = forms.CharField(max_length=11, required=False, label='VAT ID (USt-IdNr.)')
    
    class Meta:
        model = Contractor
        fields = ['full_name', 'country', 'tax_id', 'bank_account_name', 'bank_iban_or_account']
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)

        # Hide all dynamic fields initially
        dynamic_fields = ['pan', 'aadhar', 'gstin', 'cpf', 'rg', 'pis_pasep', 'steuer_id', 'ust_id']
        for field in dynamic_fields:
            self.fields[field].widget = forms.HiddenInput() 
    
    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get('country')
        
        if not country:
            return cleaned_data
        
        # Load localization engine for the selected country
        engine = LocalizationEngine(country)
        
        # Get required fields for this country
        compliance_summary = engine.get_compliance_summary()
        required_fields = [f['field'] for f in compliance_summary['required_fields']]
         # Map frontend field names to form field names
        field_mapping = {
            'pan': 'pan',
            'cpf': 'cpf',
            'steuer_id': 'steuer_id',
            'aadhar': 'aadhar',
            'gstin': 'gstin',
            'rg': 'rg',
            'pis_pasep': 'pis_pasep',
            'ust_id': 'ust_id',
        }
        # Validate required fields
        errors = {}
        for required_field in required_fields:
            form_field = field_mapping.get(required_field, required_field)
            value = cleaned_data.get(form_field, '')
            
            if not value:
                errors[form_field] = f"{required_field.upper()} is required for {engine.rules.get('name')}"
            else:
                # Validate pattern if available
                import re
                rule = next((r for r in engine.rules.get('compliance_rules', []) if r.field_name == required_field), None)
        
                if rule and rule.validation_pattern:
                    if not re.match(rule.validation_pattern, value):
                        errors[form_field] = f"Invalid format for {rule.label}. Example: {rule.example}" 

        if errors:
            raise forms.ValidationError(errors)
        
        # Store the main tax ID in the tax_id field
        main_id_field = required_fields[0] if required_fields else None
        if main_id_field:
            form_field = field_mapping.get(main_id_field, main_id_field)
            cleaned_data['tax_id'] = cleaned_data.get(form_field, '')
        
        return cleaned_data


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