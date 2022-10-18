# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0008_userprofile_user_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_college_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_college_subadmin',
            field=models.BooleanField(default=False),
        ),
    ]
