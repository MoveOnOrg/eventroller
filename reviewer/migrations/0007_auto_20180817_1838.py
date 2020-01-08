# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-08-17 18:38


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviewer', '0006_auto_20180807_2215'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reviewlog',
            options={'permissions': (('message_sending', 'message sending'), ('bulk_message_send', 'bulk message sending'), ('bulk_note_add', 'bulk note adding'))},
        ),
        migrations.AlterField(
            model_name='reviewlog',
            name='log_type',
            field=models.CharField(choices=[('note', 'Note'), ('bulknote', 'Bulk Note'), ('message', 'Message'), ('bulkmsg', 'Bulk Message')], default='note', max_length=8),
        ),
    ]
