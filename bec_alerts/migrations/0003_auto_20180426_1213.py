# Generated by Django 2.0.4 on 2018-04-26 17:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('bec_alerts', '0002_issuebucket'),
    ]

    operations = [
        migrations.AddField(
            model_name='issuebucket',
            name='date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
        migrations.AlterUniqueTogether(
            name='issuebucket',
            unique_together={('issue', 'date')},
        ),
    ]
