# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-14 17:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviewer', '0002_auto_20170602_1835'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewlog',
            name='subject',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
