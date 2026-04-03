from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'phone', 'is_site_admin', 'is_staff', 'date_joined')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительно', {
            'fields': ('phone', 'avatar', 'is_site_admin')
        }),
    )
