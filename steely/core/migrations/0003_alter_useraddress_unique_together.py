# Generated by Django 5.1.3 on 2024-11-18 05:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_useraddress'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='useraddress',
            unique_together=set(),
        ),
    ]
