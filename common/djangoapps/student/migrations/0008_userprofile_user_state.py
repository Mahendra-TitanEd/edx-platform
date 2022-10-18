# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0007_auto_20170330_0226'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='user_state',
            field=models.TextField(null=True, blank=True),
        ),
    ]
