# Generated by Django 3.2.16 on 2025-01-15 12:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tariff', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='is_hidden',
            field=models.BooleanField(default=False, verbose_name='Скрыт'),
        ),
    ]
