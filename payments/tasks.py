# payments/tasks.py
from django.core.mail import send_mail
from django.conf import settings
from .models import Payout

def process_mock_payout(payout_id):
    """Mock payout - logs and sends email (replace with real API later)"""
    try:
        payout = Payout.objects.get(id=payout_id)
        
        print(f"""
        ========================================
        🎉 MOCK PAYOUT TRIGGERED 🎉
        ========================================
        Contractor: {payout.contractor.full_name}
        Email: {payout.contractor.user.email}
        Amount: ${payout.amount_usd} USD
        Country: {payout.contractor.country}
        Bank: {payout.contractor.bank_account_name}
        ========================================
        """)
        
        # Update status
        payout.status = 'completed'
        payout.save()
        
        # Optional: Send email notification
        # send_mail(
        #     'Payment Received',
        #     f'You have received ${payout.amount_usd} USD',
        #     settings.DEFAULT_FROM_EMAIL,
        #     [payout.contractor.user.email],
        # )
        
    except Exception as e:
        print(f"Mock payout failed: {e}")