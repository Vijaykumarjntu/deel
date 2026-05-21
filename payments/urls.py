# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('stripe/connect/', views.create_stripe_connect_account, name='stripe_connect'),
    path('stripe/return/', views.stripe_return, name='stripe_return'),
    path('stripe/refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('pay/<int:contractor_id>/', views.create_checkout_session, name='create_checkout'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    # Contracts
    path('contract/create/<int:contractor_id>/', views.create_contract, name='create_contract'),
    path('contracts/', views.contract_list, name='contract_list'),
    path('contract/<int:contract_id>/', views.contract_detail, name='contract_detail'),
    path('contract/<int:contract_id>/send/', views.send_contract, name='send_contract'),
    path('contract/<int:contract_id>/sign/', views.sign_contract, name='sign_contract'),
    path('contract/<int:contract_id>/download/', views.download_contract_pdf, name='download_contract'),
]
