# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-12 23:50


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_exim', '0006_auto_20170612_2143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventdupeguesses',
            name='decision',
            field=models.IntegerField(choices=[(0, 'undecided'), (1, 'not a duplicate'), (2, 'yes, duplicates')], verbose_name='Status'),
        ),
    ]
