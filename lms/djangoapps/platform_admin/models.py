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


AUTH_METHOD_CHOICES = [
    ('SSO', 'SSO'),
    ('Direct', 'Direct registration'),
    ('Code', 'Enrolment code'),
]

SYNC_RESULT_CHOICES = [
    ('granted', 'Granted'),
    ('blocked', 'Blocked'),
]

SYNC_ACCOUNT_CHOICES = [
    ('created', 'New account'),
    ('existing', 'Returning'),
]


class SyncLogEvent(TimeStampedModel):
    """
    Sync / enrolment access log for Platform Admin.
    Records SSO logins, direct registration, and enrolment-code events.
    """
    college = models.ForeignKey(
        'college.College',
        on_delete=models.CASCADE,
        related_name='sync_log_events',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sync_log_events',
    )
    student_name = models.CharField(max_length=255)
    student_email = models.EmailField()
    auth_method = models.CharField(max_length=20, choices=AUTH_METHOD_CHOICES, default='Direct')
    programme_name = models.CharField(max_length=255, blank=True, default='')
    year_name = models.CharField(max_length=50, blank=True, default='')
    section_name = models.CharField(max_length=100, blank=True, default='')
    account_status = models.CharField(max_length=20, choices=SYNC_ACCOUNT_CHOICES, default='created')
    result = models.CharField(max_length=20, choices=SYNC_RESULT_CHOICES, default='granted')
    block_reason = models.TextField(blank=True, default='')
    event_at = models.DateTimeField(db_index=True)

    class Meta:
        app_label = 'platform_admin'
        verbose_name = 'Sync Log Event'
        verbose_name_plural = 'Sync Log Events'
        ordering = ['-event_at', '-id']
        indexes = [
            models.Index(fields=['college', '-event_at']),
            models.Index(fields=['college', 'result']),
        ]

    def __str__(self):
        return f"{self.student_email} · {self.result} · {self.event_at}"
