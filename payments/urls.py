# payments/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('stripe/connect/', views.create_stripe_connect_account, name='stripe_connect'),
    path('stripe/return/', views.stripe_return, name='stripe_return'),
    path('stripe/refresh/', views.stripe_refresh, name='stripe_refresh'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
