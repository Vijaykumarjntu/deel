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
from .models import Payout,Contract 

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

    # payments/views.py - Add these functions


# payments/views.py - Add this function before create_contract

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
# payments/views.py - Add with other imports
from django.utils import timezone

def generate_contract_pdf(contract):
    """Generate PDF contract document"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom style for title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a56db'),
        alignment=1,  # Center
        spaceAfter=30,
    )
    
    # Content list
    story = []
    
    # Title
    story.append(Paragraph(f"Independent Contractor Agreement", title_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Date
    story.append(Paragraph(f"<b>Date:</b> {contract.created_at.strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Parties
    story.append(Paragraph("<b>1. PARTIES</b>", styles['Heading4']))
    story.append(Paragraph(f"This agreement is between:", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Company:</b> {contract.company.name}", styles['Normal']))
    story.append(Paragraph(f"<b>Contractor:</b> {contract.contractor.full_name}", styles['Normal']))
    story.append(Paragraph(f"<b>Contractor Email:</b> {contract.contractor.user.email}", styles['Normal']))
    story.append(Paragraph(f"<b>Country:</b> {contract.contractor.get_country_display()}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Services
    story.append(Paragraph("<b>2. SERVICES</b>", styles['Heading4']))
    story.append(Paragraph(f"Contractor agrees to provide services as described in the scope of work for {contract.title}.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Compensation
    story.append(Paragraph("<b>3. COMPENSATION</b>", styles['Heading4']))
    story.append(Paragraph(f"<b>Hourly Rate:</b> ${contract.hourly_rate_usd} USD per hour", styles['Normal']))
    story.append(Paragraph(f"<b>Estimated Monthly Hours:</b> {contract.monthly_hours} hours", styles['Normal']))
    story.append(Paragraph(f"<b>Estimated Monthly Compensation:</b> ${contract.monthly_amount_usd} USD", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Payment Terms
    story.append(Paragraph("<b>4. PAYMENT TERMS</b>", styles['Heading4']))
    story.append(Paragraph("Company shall pay Contractor within 14 days of invoice receipt via Stripe payment platform.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Term and Termination
    story.append(Paragraph("<b>5. TERM AND TERMINATION</b>", styles['Heading4']))
    story.append(Paragraph("This agreement shall commence on the effective date and may be terminated by either party with 30 days written notice.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Independent Contractor
    story.append(Paragraph("<b>6. INDEPENDENT CONTRACTOR</b>", styles['Heading4']))
    story.append(Paragraph("Contractor is an independent contractor, not an employee. Contractor is responsible for their own taxes, benefits, and insurance.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Governing Law
    story.append(Paragraph("<b>7. GOVERNING LAW</b>", styles['Heading4']))
    story.append(Paragraph("This agreement shall be governed by the laws of the State of Delaware.", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    
    # Signature section
    story.append(Paragraph("<b>8. SIGNATURES</b>", styles['Heading4']))
    story.append(Spacer(1, 0.2 * inch))
    
    # Signature table
    sig_data = [
        ['', ''],
        ['<b>COMPANY</b>', '<b>CONTRACTOR</b>'],
        ['', ''],
        ['_________________________', '_________________________'],
        [contract.company.name, contract.contractor.full_name],
        ['', ''],
        [f'Date: {contract.created_at.strftime("%Y-%m-%d")}', 'Date: _________________'],
    ]
    
    sig_table = Table(sig_data, colWidths=[2.5 * inch, 2.5 * inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 10),
        ('TOPPADDING', (0, 3), (-1, 3), 20),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 20),
    ]))
    story.append(sig_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

@login_required
def create_contract(request, contractor_id):
    """Company creates contract for contractor"""
    
    if request.user.role != 'company':
        messages.error(request, 'Only companies can create contracts')
        return redirect('dashboard')
    
    try:
        contractor = Contractor.objects.get(id=contractor_id, company=request.user.company)
    except Contractor.DoesNotExist:
        messages.error(request, 'Contractor not found')
        return redirect('contractor_list')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        hourly_rate = request.POST.get('hourly_rate')
        monthly_hours = request.POST.get('monthly_hours')
        
        # Create contract
        contract = Contract.objects.create(
            contractor=contractor,
            company=request.user.company,
            title=title,
            hourly_rate_usd=hourly_rate,
            monthly_hours=monthly_hours,
            status='draft'
        )
        
        # Generate PDF
        pdf_content = generate_contract_pdf(contract)
        contract.pdf_file.save(f"contract_{contract.id}.pdf", ContentFile(pdf_content))
        contract.save()
        
        messages.success(request, f'Contract "{title}" created successfully!')
        return redirect('contract_detail', contract_id=contract.id)
    
    return render(request, 'payments/create_contract.html', {
        'contractor': contractor,
    })


@login_required
def contract_list(request):
    """List contracts (company or contractor view)"""
    if request.user.role == 'company':
        contracts = Contract.objects.filter(company=request.user.company).order_by('-created_at')
    elif request.user.role == 'contractor':
        contracts = Contract.objects.filter(contractor=request.user.contractor).order_by('-created_at')
    else:
        contracts = []
    
    return render(request, 'payments/contract_list.html', {'contracts': contracts})


@login_required
def contract_detail(request, contract_id):
    """View contract details"""
    try:
        if request.user.role == 'company':
            contract = Contract.objects.get(id=contract_id, company=request.user.company)
        else:
            contract = Contract.objects.get(id=contract_id, contractor=request.user.contractor)
    except Contract.DoesNotExist:
        messages.error(request, 'Contract not found')
        return redirect('dashboard')
    
    return render(request, 'payments/contract_detail.html', {'contract': contract})


@login_required
def send_contract(request, contract_id):
    """Company sends contract to contractor"""
    if request.user.role != 'company':
        messages.error(request, 'Only companies can send contracts')
        return redirect('dashboard')
    
    contract = get_object_or_404(Contract, id=contract_id, company=request.user.company)
    
    if contract.status != 'draft':
        messages.warning(request, 'Contract already sent or signed')
        return redirect('contract_detail', contract_id=contract.id)
    
    contract.status = 'sent'
    contract.sent_at = timezone.now()
    contract.save()
    
    messages.success(request, f'Contract sent to {contract.contractor.full_name}')
    return redirect('contract_detail', contract_id=contract.id)


@login_required
def sign_contract(request, contract_id):
    """Contractor signs contract"""
    if request.user.role != 'contractor':
        messages.error(request, 'Only contractors can sign contracts')
        return redirect('dashboard')
    
    contract = get_object_or_404(Contract, id=contract_id, contractor=request.user.contractor)
    
    if contract.status in ['signed', 'active']:
        messages.warning(request, 'Contract already signed')
        return redirect('contract_detail', contract_id=contract.id)
    
    if request.method == 'POST':
        contract.status = 'signed'
        contract.signed_at = timezone.now()
        contract.signed_ip = get_client_ip(request)
        contract.save()
        
        messages.success(request, 'Contract signed successfully!')
        return redirect('contract_detail', contract_id=contract.id)
    
    return render(request, 'payments/sign_contract.html', {'contract': contract, 'now': timezone.now()})


@login_required
def download_contract_pdf(request, contract_id):
    """Download contract PDF"""
    if request.user.role == 'company':
        contract = get_object_or_404(Contract, id=contract_id, company=request.user.company)
    else:
        contract = get_object_or_404(Contract, id=contract_id, contractor=request.user.contractor)
    
    if contract.pdf_file:
        response = HttpResponse(contract.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="contract_{contract.id}.pdf"'
        return response
    
    raise Http404("PDF not found")


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip