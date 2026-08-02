# Generated manually for SyncLogEvent

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('college', '0012_alter_college_timezone'),
        ('platform_admin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SyncLogEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('student_name', models.CharField(max_length=255)),
                ('student_email', models.EmailField(max_length=254)),
                ('auth_method', models.CharField(choices=[('SSO', 'SSO'), ('Direct', 'Direct registration'), ('Code', 'Enrolment code')], default='Direct', max_length=20)),
                ('programme_name', models.CharField(blank=True, default='', max_length=255)),
                ('year_name', models.CharField(blank=True, default='', max_length=50)),
                ('section_name', models.CharField(blank=True, default='', max_length=100)),
                ('account_status', models.CharField(choices=[('created', 'New account'), ('existing', 'Returning')], default='created', max_length=20)),
                ('result', models.CharField(choices=[('granted', 'Granted'), ('blocked', 'Blocked')], default='granted', max_length=20)),
                ('block_reason', models.TextField(blank=True, default='')),
                ('event_at', models.DateTimeField(db_index=True)),
                ('college', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sync_log_events', to='college.College')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sync_log_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sync Log Event',
                'verbose_name_plural': 'Sync Log Events',
                'ordering': ['-event_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='synclogevent',
            index=models.Index(fields=['college', '-event_at'], name='platform_ad_college_7f6e2a_idx'),
        ),
        migrations.AddIndex(
            model_name='synclogevent',
            index=models.Index(fields=['college', 'result'], name='platform_ad_college_2c8a91_idx'),
        ),
    ]
