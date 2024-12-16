# Generated by Django 5.1.3 on 2024-11-30 18:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_order_customer_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='address_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders_address', to='core.useraddress'),
        ),
    ]