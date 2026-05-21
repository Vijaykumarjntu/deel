from django.contrib import admin

# Register your models here.
from .models import Contract, Payout, WebhookEvent
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('title', 'contractor', 'status', 'monthly_amount_usd')
    list_filter = ('status',)

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('contract', 'amount_usd', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'event_id', 'processed', 'received_at')
    list_filter = ('processed', 'event_type')