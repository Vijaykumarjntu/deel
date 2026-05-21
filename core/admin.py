# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Contractor

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Role', {'fields': ('role',)}),
    )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'stripe_verified', 'created_at')
    search_fields = ('name', 'user__email')

@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company', 'country', 'is_active')
    list_filter = ('country', 'is_active')
    search_fields = ('full_name', 'user__email')

