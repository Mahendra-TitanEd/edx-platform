# Migration to add allocated_seats field and unique_together constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('university_programme', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='universityprogrammes',
            name='allocated_seats',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterUniqueTogether(
            name='universityprogrammes',
            unique_together={('university', 'short_name')},
        ),
    ]
