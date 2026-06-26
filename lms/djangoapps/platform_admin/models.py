"""
Platform Admin Models
"""

from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel


FACULTY_TYPE_CHOICES = [
    ('teaching', 'Teaching'),
    ('placement', 'Placement'),
]

PLACEMENT_ACCESS_CHOICES = [
    ('track_only', 'Track Only'),
    ('all_tracks', 'All Tracks'),
]


class FacultyAdmin(TimeStampedModel):
    """
    Faculty Admin Model
    Stores additional information about faculty members beyond User and UserMetaData
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='faculty_admin'
    )

    faculty_type = models.CharField(
        max_length=20,
        choices=FACULTY_TYPE_CHOICES,
        default='teaching',
        help_text="Type of faculty: Teaching or Placement"
    )

    programmes = models.ManyToManyField(
        'university_programme.UniversityProgrammes',
        related_name='faculty_admins',
        blank=True,
        help_text="Programmes this faculty has access to"
    )

    placement_access = models.CharField(
        max_length=20,
        choices=PLACEMENT_ACCESS_CHOICES,
        null=True,
        blank=True,
        help_text="Placement access level (only for Placement faculty)"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this faculty admin is active"
    )

    class Meta:
        app_label = 'platform_admin'
        verbose_name = 'Faculty Admin'
        verbose_name_plural = 'Faculty Admins'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_faculty_type_display()}"

    def get_programmes_list(self):
        """Returns list of programme short names"""
        return [prog.short_name for prog in self.programmes.all()]

    def has_careers_app_access(self):
        """Returns True if this faculty should have Careers App access"""
        return self.faculty_type == 'placement'
