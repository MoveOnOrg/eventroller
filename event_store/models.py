from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, Group

class Organization(models.Model):
    title = models.CharField(max_length=765)
    facebook = models.CharField(max_length=128)
    twitter = models.CharField(max_length=128, help_text="do not include @")
    url = models.URLField(blank=True)
    slug = models.CharField(max_length=128)

    logo_thumb = models.URLField(blank=True)
    logo_big = models.URLField(blank=True)
    privacy_policy = models.URLField(blank=True)
    terms_and_conditions = models.URLField(blank=True)

    #default source id
    osdi_source_id = models.CharField(max_length=128)

    group = models.ForeignKey(Group)
    # for getting other folks' data; auto/re-generatable
    api_key = models.CharField(max_length=765, editable=False)


class Activist(models.Model):
    hashed_email = models.CharField(max_length=765, null=True, blank=True)
    email = models.CharField(max_length=765, null=True, blank=True)
    name = models.CharField(max_length=765, null=True, blank=True)
    member_system_id = models.CharField(max_length=765)


EVENT_REVIEW_CHOICES = (('', 'New'),
                        ('reviewed', 'Reviewed'),
                        ('vetted', 'Vetted'),
                        ('questionable', 'Questionable'),
                        ('limbo', 'Limbo'))

EVENT_PREP_CHOICES = (('', 'Unclaimed'),
                      ('claimed', 'Claimed'),
                      ('partially_prepped', 'Partially prepped'),
                      ('fully_prepped', 'Fully prepped'),
                      ('nocontact', 'Unable to contact'))

class Event(models.Model):
    #starting with ActionKit baseline, out of selfishness
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    address1 = models.CharField(max_length=765, null=True, blank=True)
    address2 = models.CharField(max_length=765, null=True, blank=True)
    city = models.CharField(max_length=765, null=True, blank=True)
    state = models.CharField(max_length=765, null=True, blank=True)
    region = models.CharField(max_length=765, null=True, blank=True)
    postal = models.CharField(max_length=765, null=True, blank=True)
    zip = models.CharField(max_length=15, null=True, blank=True)
    plus4 = models.CharField(max_length=12, null=True, blank=True)
    country = models.CharField(max_length=765, null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    title = models.CharField(max_length=765)

    starts_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    starts_at_utc = models.DateTimeField(null=True, blank=True)
    ends_at_utc = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=96, db_index=True,
                              choices=(('active', 'active'),
                                       ('cancelled', 'cancelled'),
                                       ('deleted', 'deleted'),
                                   ))
    host_is_confirmed = models.IntegerField()
    is_private = models.IntegerField(choices=((0, 'public'), (1, 'private')),
                                     verbose_name="private or public")
    is_approved = models.IntegerField()
    attendee_count = models.IntegerField()
    max_attendees = models.IntegerField(null=True, blank=True)
    venue = models.CharField(max_length=765)
    phone = models.CharField(max_length=765)
    public_description = models.TextField()
    directions = models.TextField()
    note_to_attendees = models.TextField()
    notes = models.TextField()

    #from ground-control
    #eventIdObfuscated: {type: GraphQLString},
    organization_official_event = models.NullBooleanField(null=True)
    event_type = models.CharField(max_length=765)
    organization_host = models.ForeignKey('Activist', blank=True, null=True)
    organization = models.ForeignKey('Organization', blank=True, null=True, db_index=True)
    organization_source = models.ForeignKey('event_exim.EventSource', blank=True, null=True, db_index=True)
    organization_campaign = models.CharField(max_length=765, db_index=True)

    #hostId: {type: GraphQLString}, = add primary_host
    #localTimezone: {type: GraphQLString}, #not there, but starts_at + starts_at_utc sorta does that
    #duration: {type: GraphQLInt},
    is_searchable = models.IntegerField(choices=((0, 'not searchable'), (1, 'searchable')))
    private_phone = models.CharField(max_length=765)
    
    #?todo
    #hostReceiveRsvpEmails: {type: GraphQLBoolean},
    #rsvpUseReminderEmail: {type: GraphQLBoolean},
    #rsvpEmailReminderHours: {type: GraphQLInt},

    #from progressive events
    url = models.URLField(blank=True)
    #if present, does not need to be unique -- though probably should be by organization+campaign+eventtype
    slug = models.SlugField(blank=True, null=True, max_length=255)

    #someday: https://github.com/django-recurrence/django-recurrence
    #recurrences = MoneypatchedRecurrenceField(null=True)

    #osdi
    osdi_origin_system = models.CharField(max_length=765)
    #ticket_levels[]
    ticket_type = models.IntegerField(choices=((0, 'ticketed'), (1, 'open'), (2, 'ticketed')))
    share_url = models.URLField(blank=True)
    #share_options[] = facebook_share{title, desc, img}, twitter_share{msg}, email_share{subj,body}

    political_scope = models.CharField(max_length=765, null=True, blank=True) #ocdep, districts, etc maybe

    dupe_id = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    venue_category = models.IntegerField(choices=((0, 'unknown'),
                                                  (1, 'private home'),
                                                  (2, 'public space'),
                                                  (3, 'target location (e.g. congressional district office)'),
                                                  (4, 'virtual'),
                                              ))

    needs_organizer_help = models.IntegerField(null=True, blank=True, default=0)

    #these can be functions of the source:
    rsvp_url = models.URLField(blank=True)
    event_facebook_url = models.URLField(blank=True)
    organization_status_review = models.CharField(max_length=32, blank=True, db_index=True,
                                                  choices=EVENT_REVIEW_CHOICES)
    organization_status_prep = models.CharField(max_length=32, blank=True, db_index=True,
                                                choices=EVENT_PREP_CHOICES)

    #later
    def host_edit_url(self):
        pass #organization can implement

    def handle_rsvp(self):
        return None #organization can implement
