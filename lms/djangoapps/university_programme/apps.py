"""
Django app configuration for University Programme
"""

from django.apps import AppConfig


class UniversityProgrammeConfig(AppConfig):
    """
    Configuration for the University Programme application
    """
    name = 'lms.djangoapps.university_programme'
    verbose_name = 'University Programme'

    def ready(self):
        """
        Application initialization
        """
        pass
