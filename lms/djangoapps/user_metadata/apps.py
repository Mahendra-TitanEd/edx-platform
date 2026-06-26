"""
User Metadata App Configuration
"""
from django.apps import AppConfig


class UserMetadataConfig(AppConfig):
    name = 'lms.djangoapps.user_metadata'
    verbose_name = 'User Metadata'
    default_auto_field = 'django.db.models.BigAutoField'
