"""
Django app configuration for Platform Admin
"""

from django.apps import AppConfig


class PlatformAdminConfig(AppConfig):
    """
    Configuration for the Platform Admin application
    """
    name = 'lms.djangoapps.platform_admin'
    verbose_name = 'Platform Administration'

    def ready(self):
        """
        Application initialization
        """
        pass
