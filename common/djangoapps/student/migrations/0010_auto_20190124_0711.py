# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0009_auto_20190124_0400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='is_college_admin',
            field=models.BooleanField(default=False, verbose_name=b'College Admin'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='is_college_subadmin',
            field=models.BooleanField(default=False, verbose_name=b'College Sub-Admin'),
        ),
    ]
