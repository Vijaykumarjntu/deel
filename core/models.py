# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class User(AbstractUser):
    """Custom user model"""
    ROLE_CHOICES = (
        ('company', 'Company Admin'),
        ('contractor', 'Contractor'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='company')
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',  # Changed from default
        blank=True,
        verbose_name='groups',
        help_text='The groups this user belongs to.',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',  # Changed from default
        blank=True,
        verbose_name='user permissions',
        help_text='Specific permissions for this user.',
    )
    
    def __str__(self):
        return f"{self.email} ({self.role})"

class Company(models.Model):
    """Company that hires contractors"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company')
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    
    # Stripe Connect fields
    stripe_account_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_verified = models.BooleanField(default=False)
    stripe_verification_status = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Contractor(models.Model):
    """Contractor hired by a company"""
    COUNTRY_CHOICES = (
        ('IN', 'India'),
        ('BR', 'Brazil'),
        ('DE', 'Germany'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='contractor')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contractors')
    
    # Personal details
    full_name = models.CharField(max_length=255)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    
    # Tax IDs for different countries
    tax_id = models.CharField(max_length=50, help_text="PAN (India), CPF (Brazil), Steuer-ID (Germany)")
    
    # Bank/Payment details
    bank_account_name = models.CharField(max_length=255)
    bank_iban_or_account = models.CharField(max_length=100)  # IBAN for DE, account number for IN/BR
    
    # Mock payout fields (will be used later)
    mock_recipient_id = models.CharField(max_length=100, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # class Meta:
    #     unique_together = ['company', 'email']  # Same contractor can't be added twice to same company
    
    def __str__(self):
        return f"{self.full_name} ({self.company.name})"
    
    # @property
    # def email(self):
    #     return self.user.email
