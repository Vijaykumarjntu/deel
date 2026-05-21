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
# import stripe
# import json
# from django.conf import settings
# from django.http import HttpResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
# from .models import WebhookEvent

# stripe.api_key = settings.STRIPE_SECRET_KEY

# @csrf_exempt
# @require_http_methods(["POST"])
# def stripe_webhook(request):
#     """Handle Stripe webhook events"""
#     payload = request.body
#     sig_header = request.headers.get('Stripe-Signature')
    
#     print(f"Webhook received. Signature present: {bool(sig_header)}")
#     print("this is the key")
#     print(stripe.api_key)
#     # Verify webhook signature
#     try:
#         event = stripe.Webhook.construct_event(
#             payload, 
#             sig_header, 
#             settings.STRIPE_WEBHOOK_SECRET
#         )
#     except ValueError as e:
#         print(f"Invalid payload: {e}")
#         return HttpResponse("Invalid payload", status=400)
#     except stripe.error.SignatureVerificationError as e:
#         print(f"Invalid signature: {e}")
#         return HttpResponse("Invalid signature", status=400)
    
#     event_id = event['id']
#     event_type = event['type']
    
#     print(f"Processing webhook: {event_type} - {event_id}")
    
#     # Idempotency check - prevent duplicate processing
#     webhook_event, created = WebhookEvent.objects.get_or_create(
#         event_id=event_id,
#         defaults={
#             'event_type': event_type,
#             'processed': False
#         }
#     )
    
#     if not created and webhook_event.processed:
#         print(f"Event {event_id} already processed, skipping")
#         return HttpResponse("Already processed", status=200)
    
#     # Handle different event types
#     if event_type == 'payment_intent.succeeded':
#         payment_intent = event['data']['object']
#         print(f"✅ Payment succeeded: {payment_intent['id']}")
#         print(f"   Amount: {payment_intent['amount']} {payment_intent['currency']}")
#         # TODO: Trigger payout to contractor
        
#     elif event_type == 'payment_intent.created':
#         payment_intent = event['data']['object']
#         print(f"📝 Payment created: {payment_intent['id']}")
        
#     elif event_type == 'payment_intent.payment_failed':
#         payment_intent = event['data']['object']
#         print(f"❌ Payment failed: {payment_intent['id']}")
#         print(f"   Error: {payment_intent.get('last_payment_error', {}).get('message')}")
        
#     elif event_type == 'account.updated':
#         account = event['data']['object']
#         print(f"🏦 Account updated: {account['id']}")
#         print(f"   Charges enabled: {account.get('charges_enabled')}")
#         print(f"   Payouts enabled: {account.get('payouts_enabled')}")
        
#     else:
#         print(f"⚠️ Unhandled event type: {event_type}")
    
#     # Mark as processed
#     webhook_event.processed = True
#     webhook_event.save()
    
#     return HttpResponse("OK", status=200)

    # payments/views.py
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