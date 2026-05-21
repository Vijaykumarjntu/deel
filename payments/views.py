from django.shortcuts import render

# Create your views here.
# payments/views.py
import stripe
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_stripe_connect_account(request):
    """Create Stripe Connect account for company"""
    try:
        company = request.user.company
        
        if company.stripe_account_id:
            messages.info(request, 'Stripe account already connected')
            return redirect('dashboard')
        
        account = stripe.Account.create(
            type='express',
            country='US',
            email=request.user.email,
            capabilities={'transfers': {'requested': True}},
        )
        
        company.stripe_account_id = account.id
        company.save()
        
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=request.build_absolute_uri('/payments/stripe/refresh/'),
            return_url=request.build_absolute_uri('/payments/stripe/return/'),
            type='account_onboarding',
        )
        
        return redirect(account_link.url)
        
    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe error: {str(e)}')
        return redirect('dashboard')

@login_required
def stripe_return(request):
    company = request.user.company
    account = stripe.Account.retrieve(company.stripe_account_id)
    
    if account.charges_enabled and account.payouts_enabled:
        company.stripe_verified = True
        company.save()
        messages.success(request, 'Stripe connected!')
    else:
        messages.warning(request, 'Verification pending')
    
    return redirect('dashboard')

@login_required
def stripe_refresh(request):
    messages.warning(request, 'Please complete Stripe onboarding')
    return redirect('dashboard')


# payments/views.py
import stripe
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from core.models import Contractor
from .models import Payout

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session(request, contractor_id):
    """Create Stripe Checkout session to pay a contractor"""
    
    if request.user.role != 'company':
        messages.error(request, 'Only companies can make payments')
        return redirect('dashboard')
    
    try:
        contractor = Contractor.objects.get(id=contractor_id, company=request.user.company)
    except Contractor.DoesNotExist:
        messages.error(request, 'Contractor not found')
        return redirect('contractor_list')
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        try:
            # Convert to cents for Stripe
            amount_cents = int(float(amount) * 100)
            
            # Create Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Payment to {contractor.full_name}',
                            'description': f'Contractor payment for {contractor.company.name}',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(reverse('payment_success')) + f'?session_id={{CHECKOUT_SESSION_ID}}&contractor_id={contractor_id}',
                cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
                metadata={
                    'contractor_id': contractor_id,
                    'company_id': request.user.company.id,
                    'amount_usd': amount,
                }
            )
            
            # Save payout record
            Payout.objects.create(
                contractor=contractor,
                company=request.user.company,
                amount_usd=amount,
                stripe_payment_intent_id=checkout_session.id,
                status='pending'
            )
            
            return redirect(checkout_session.url, code=303)
            
        except stripe.error.StripeError as e:
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('contractor_list')
    
    return render(request, 'payments/create_checkout.html', {
        'contractor': contractor,
    })

# payments/views.py
from .models import Payout, WebhookEvent

@login_required
def payment_success(request):
    """Handle successful payment redirect"""
    session_id = request.GET.get('session_id')
    contractor_id = request.GET.get('contractor_id')
    
    try:
        # Retrieve checkout session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Update payout record
        payout = Payout.objects.filter(stripe_payment_intent_id=session_id).first()
        if payout:
            payout.status = 'processing'
            payout.save()
        
        messages.success(request, f'Payment of ${session.amount_total/100} USD successful!')
        
        # Trigger mock payout (will replace with real later)
        from .tasks import process_mock_payout
        process_mock_payout(payout.id)
        
    except Exception as e:
        messages.error(request, f'Error processing payment: {str(e)}')
    
    return redirect('contractor_list')

@login_required
def payment_cancel(request):
    """Handle cancelled payment"""
    messages.warning(request, 'Payment was cancelled')
    return redirect('contractor_list')

    
import stripe
import json
import logging
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    
    payload = request.body

    sig_header = request.headers.get('Stripe-Signature', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    print(f"Raw payload type: {type(payload)}")
    print(f"First 100 bytes: {payload[:100]}")
    print(f"Sig header full: {sig_header}")
    print(f"=== WEBHOOK RECEIVED ===")
    print(f"Signature header present: {bool(sig_header)}")
    print(f"Webhook secret present: {bool(webhook_secret)}")
    print(webhook_secret)
    print(f"Payload length: {len(payload)}")
    
    if not webhook_secret:
        print("❌ ERROR: STRIPE_WEBHOOK_SECRET not set in settings")
        return HttpResponse("Webhook secret not configured", status=500)
    
    try:
        # Construct the event
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        print(f"❌ Invalid payload: {e}")
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"❌ Invalid signature: {e}")
        print(f"Expected signature: {sig_header[:50]}...")
        return HttpResponse("Invalid signature", status=400)
    
    # Handle the event
    event_type = event['type']
    event_id = event['id']
    
    print(f"✅ Webhook verified: {event_type} - {event_id}")
    
    if event_type == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"💰 Payment succeeded: {payment_intent['id']}")
        print(f"   Amount: {payment_intent['amount']} {payment_intent['currency']}")
        
    elif event_type == 'payment_intent.created':
        payment_intent = event['data']['object']
        print(f"📝 Payment created: {payment_intent['id']}")
        
    elif event_type == 'payment_intent.requires_action':
        payment_intent = event['data']['object']
        print(f"🔐 Requires action: {payment_intent['id']}")
        
    else:
        print(f"⚠️ Unhandled event type: {event_type}")
    
    return HttpResponse("OK", status=200)