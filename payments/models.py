# from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Contract(models.Model):
    """Contract between company and contractor"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent to Contractor'),
        ('signed', 'Signed'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    )
    
    contractor = models.ForeignKey('core.Contractor', on_delete=models.CASCADE, related_name='contracts')
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='contracts')
    
    # Contract details
    title = models.CharField(max_length=255)
    hourly_rate_usd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    monthly_hours = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(744)])
    
    # Contract files
    pdf_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    signed_pdf = models.FileField(upload_to='contracts/signed/', blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(blank=True, null=True)
    signed_at = models.DateTimeField(blank=True, null=True)
    signed_ip = models.GenericIPAddressField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.contractor.full_name}"
    
    @property
    def monthly_amount_usd(self):
        return self.hourly_rate_usd * self.monthly_hours

class Payout(models.Model):
    """Record of payments to contractors"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    )
    
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='payouts')
    contractor = models.ForeignKey('core.Contractor', on_delete=models.CASCADE, related_name='payouts')
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='payouts')
    
    # Payment details
    amount_usd = models.DecimalField(max_digits=10, decimal_places=2)
    amount_local = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    local_currency = models.CharField(max_length=3, blank=True, null=True)  # INR, BRL, EUR
    
    # Stripe payment
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    
    # Payout tracking
    mock_transfer_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    # initiated_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"Payout ${self.amount_usd} to {self.contractor.full_name} ({self.status})"

class WebhookEvent(models.Model):
    """For idempotency — prevent duplicate webhook processing"""
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.event_type} - {self.event_id}"