# Generated by Django 5.1.3 on 2024-11-11 12:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_remove_productimage_is_delete_product_is_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='is_delete',
            field=models.BooleanField(default=True),
        ),
    ]
