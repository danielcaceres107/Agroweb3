# Generated by Django 4.1.8 on 2023-04-24 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mysite', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dimvendedores',
            name='password',
            field=models.BinaryField(max_length='max'),
        ),
    ]