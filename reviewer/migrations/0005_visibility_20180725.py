# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-07-25 13:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviewer', '0004_review_iscurrent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='review',
            name='is_current',
        ),
        migrations.AddField(
            model_name='review',
            name='obsoleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='review',
            name='visibility_level',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reviewgroup',
            name='visibility_level',
            field=models.IntegerField(default=0, help_text='Think of it like an access hierarchy. 0 is generally the lowest level. Anything higher is probably staff/etc. It affects what Reviews and Notes will be visible'),
        ),
        migrations.AddField(
            model_name='reviewlog',
            name='visibility_level',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]