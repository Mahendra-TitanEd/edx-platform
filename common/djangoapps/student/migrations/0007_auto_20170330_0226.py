# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # ('student', '0006_logoutviewconfiguration'),
        ('student', '0001_squashed_0031_auto_20200317_1122'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseenrollment',
            name='mode',
            field=models.CharField(default=b'honor', max_length=100),
        ),
        migrations.AlterField(
            model_name='historicalcourseenrollment',
            name='mode',
            field=models.CharField(default=b'honor', max_length=100),
        ),
    ]
