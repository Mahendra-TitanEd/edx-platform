"""
User Metadata Models

Extended user information and metadata.
"""

from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel


USER_STATUS_CHOICES = [
   ('active', 'Active'),
   ('suspended', 'Suspended'),
   ('pending', 'Pending'),
   ('archived', 'Archived'),
   ('inactive', 'Inactive'),
]


class UserMetaData(TimeStampedModel):
   """User Metadata - Extended user information"""
   user = models.OneToOneField(
       User,
       on_delete=models.CASCADE,
       related_name='metadata',
       primary_key=True
   )
   status = models.CharField(max_length=20, choices=USER_STATUS_CHOICES, default='pending')
   studio = models.BooleanField(default=False)
   careers_app = models.BooleanField(default=True)


   class Meta:
       app_label = 'user_metadata'
       verbose_name = 'User Metadata'
       verbose_name_plural = 'User Metadata'


   def _str_(self):
       return f"Metadata for {self.user.username}"
