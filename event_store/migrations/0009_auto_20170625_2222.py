# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models
from django.contrib.gis.geos import Point

def migrate_latlng_points(apps, schema_editor):
    Event = apps.get_model('event_store', 'Event')
    for event in Event.objects.filter(longitude__isnull=False, latitude__isnull=False):
        event.point = Point(event.longitude, event.latitude, srid=4326)
        event.save()

class Migration(migrations.Migration):

    dependencies = [
        ('event_store', '0008_auto_20170616_1506'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='point',
            field=django.contrib.gis.db.models.fields.PointField(null=True, blank=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='event',
            name='organization_status_review',
            field=models.CharField(blank=True, choices=[(None, 'New'), ('reviewed', 'Reviewed'), ('vetted', 'Vetted'), ('questionable', 'Questionable'), ('limbo', 'Limbo')], db_index=True, max_length=32, null=True),
        ),
        migrations.RunPython(migrate_latlng_points, lambda apps, schema_editor: None),
    ]
