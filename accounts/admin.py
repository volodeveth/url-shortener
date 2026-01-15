from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'plan', 'date_joined', 'is_active']
    list_filter = ['plan', 'is_active', 'is_staff']
    search_fields = ['username', 'email']

    fieldsets = UserAdmin.fieldsets + (
        ('Subscription', {
            'fields': ('plan', 'plan_expires', 'api_key')
        }),
    )
