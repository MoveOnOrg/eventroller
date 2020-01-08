# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-02 18:35


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_store', '0004_auto_20170531_1514'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='ticket_type',
            field=models.IntegerField(choices=[(0, 'unknown'), (1, 'open'), (2, 'ticketed')]),
        ),
        migrations.AlterField(
            model_name='organization',
            name='facebook',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AlterField(
            model_name='organization',
            name='slug',
            field=models.SlugField(max_length=128),
        ),
        migrations.AlterField(
            model_name='organization',
            name='twitter',
            field=models.CharField(blank=True, help_text='do not include @', max_length=128, null=True),
        ),
    ]
