# Generated by Django 5.1.3 on 2024-11-10 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='is_delete',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='productvariant',
            name='is_delete',
            field=models.BooleanField(default=True),
        ),
    ]
