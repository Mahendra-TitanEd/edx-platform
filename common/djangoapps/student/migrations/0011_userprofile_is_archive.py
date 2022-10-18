# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0010_auto_20190124_0711'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_archive',
            field=models.BooleanField(default=False, verbose_name=b'Archived User'),
        ),
    ]
