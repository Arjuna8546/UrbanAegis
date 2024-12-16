# Generated by Django 5.1.3 on 2024-12-01 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_wallet_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallettransaction',
            name='razorpay_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='razorpay_payment_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='razorpay_signature_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]