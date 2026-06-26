"""
User Metadata Admin Configuration
"""
from django.contrib import admin
from .models import UserMetaData


@admin.register(UserMetaData)
class UserMetaDataAdmin(admin.ModelAdmin):
    """Admin for User Metadata"""
    list_display = (
        'user',
        'get_username',
        'get_email',
        'status',
        'studio',
        'careers_app',
        'created',
        'modified'
    )
    list_filter = ('status', 'studio', 'careers_app')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created', 'modified')
    raw_id_fields = ('user',)

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Metadata', {
            'fields': ('status', 'studio', 'careers_app')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    def get_username(self, obj):
        """Get username from related user"""
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'

    def get_email(self, obj):
        """Get email from related user"""
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'
