"""
University Programme Models

Database models for university programmes, batches, groups, and enrollments.
"""

from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel


DURATION_CHOICES = [
   ('1_year', '1 Year'),
   ('2_year', '2 Year'),
   ('3_year', '3 Year'),
   ('4_year', '4 Year'),
   ('5_year', '5 Year'),
]


PROGRAMME_STATUS_CHOICES = [
   ('active', 'Active'),
   ('inactive', 'Inactive'),
]


GROUP_TYPE_CHOICES = [
   ('career_track', 'Career Track'),
   ('teaching_group', 'Teaching Group'),
]


class UniversityProgrammes(TimeStampedModel):
   """University Programmes"""
   short_name = models.CharField(max_length=255)
   university = models.ForeignKey('college.College', on_delete=models.CASCADE)
   name = models.CharField(max_length=1024)
   description = models.TextField(null=True, blank=True)
   duration = models.CharField(max_length=20, choices=DURATION_CHOICES, default='1_year')
   enable_careers_app = models.BooleanField(default=False)
   enable_mystudio = models.BooleanField(default=True)
   status = models.CharField(max_length=20, choices=PROGRAMME_STATUS_CHOICES, default='active')
   color = models.CharField(max_length=50, null=True, blank=True)
   allocated_seats = models.IntegerField(default=0)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Programme'
       verbose_name_plural = 'University Programmes'
       unique_together = ('university', 'short_name')


   def __str__(self):
       return f"{self.short_name} - {self.name}"

   def get_duration_years(self):
       """Extract numeric value from duration"""
       return int(self.duration.split('_')[0])

   def get_student_count(self):
       """Get count of enrolled students"""
       return self.universityprogrammesenrolment_set.filter(is_active=True).count()


class UniversityProgrammesYear(TimeStampedModel):
   """University Programmes Year"""

   programme = models.ForeignKey(
       UniversityProgrammes,
       on_delete=models.CASCADE,
       related_name='programme_years'
   )
   number_of_year = models.CharField(max_length=50)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Programme Year'
       verbose_name_plural = 'University Programme Years'


   def __str__(self):
       return f"{self.programme.short_name} - Year {self.number_of_year}"


class UniversityProgrammesYearSection(TimeStampedModel):
   """University Programmes Year Section"""

   programme_year = models.ForeignKey(
       UniversityProgrammesYear,
       on_delete=models.CASCADE,
       related_name='year_sections'
   )
   name = models.CharField(max_length=100)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Programme Year Section'
       verbose_name_plural = 'University Programme Year Sections'


   def __str__(self):
       return f"{self.programme_year} - Section {self.name}"


class UniversityProgrammesEnrolment(TimeStampedModel):
   """University Programmes Enrolment"""

   programme = models.ForeignKey(
       UniversityProgrammes,
       on_delete=models.CASCADE
   )
   programme_year = models.ForeignKey(
       UniversityProgrammesYear,
       on_delete=models.CASCADE
   )
   programme_section = models.ForeignKey(
       UniversityProgrammesYearSection,
       on_delete=models.CASCADE
   )
   user = models.ForeignKey(
       User,
       on_delete=models.CASCADE,
       related_name='programme_enrolments'
   )
   is_active = models.BooleanField(default=True)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Programme Enrolment'
       verbose_name_plural = 'University Programme Enrolments'
       unique_together = ('programme', 'user')


   def __str__(self):
       return f"{self.user.username} enrolled in {self.programme.short_name}"


class UniversityBatch(TimeStampedModel):
   """University Batch"""

   name = models.CharField(max_length=255)
   university = models.ForeignKey('college.College', on_delete=models.CASCADE)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Batch'
       verbose_name_plural = 'University Batches'


   def __str__(self):
       return self.name


class UniversityGroup(TimeStampedModel):
   """University Group"""
   name = models.CharField(max_length=255)
   university = models.ForeignKey('college.College', on_delete=models.CASCADE)
   programme = models.ForeignKey(
       UniversityProgrammes,
       on_delete=models.CASCADE,
   )
   group_type = models.CharField(max_length=50, choices=GROUP_TYPE_CHOICES)
   admin = models.CharField(max_length=255)
   description = models.TextField(null=True, blank=True)
   students = models.ManyToManyField(User, blank=True)
   colour = models.CharField(max_length=50, null=True, blank=True)


   class Meta:
       app_label = 'university_programme'
       verbose_name = 'University Group'
       verbose_name_plural = 'University Groups'


   def __str__(self):
       return f"{self.name} ({self.get_group_type_display()})"
