# Generated migration file

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('university_programme', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacultyAdmin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('faculty_type', models.CharField(
                    choices=[('teaching', 'Teaching'), ('placement', 'Placement')],
                    default='teaching',
                    help_text='Type of faculty: Teaching or Placement',
                    max_length=20
                )),
                ('placement_access', models.CharField(
                    blank=True,
                    choices=[('track_only', 'Track Only'), ('all_tracks', 'All Tracks')],
                    help_text='Placement access level (only for Placement faculty)',
                    max_length=20,
                    null=True
                )),
                ('is_active', models.BooleanField(default=True, help_text='Whether this faculty admin is active')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='faculty_admin',
                    to=settings.AUTH_USER_MODEL
                )),
                ('programmes', models.ManyToManyField(
                    blank=True,
                    help_text='Programmes this faculty has access to',
                    related_name='faculty_admins',
                    to='university_programme.UniversityProgrammes'
                )),
            ],
            options={
                'verbose_name': 'Faculty Admin',
                'verbose_name_plural': 'Faculty Admins',
            },
        ),
    ]
