from __future__ import unicode_literals
import hashlib

from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.postgres.fields import JSONField

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

    def __str__(self):
        return self.title


class Activist(models.Model):
    hashed_email = models.CharField(max_length=64, null=True, blank=True,
                                    help_text="sha256 hash hexdigest of the email address")
    email = models.CharField(max_length=765, null=True, blank=True)
    name = models.CharField(max_length=765, null=True, blank=True)
    member_system_pk = models.CharField(max_length=765, null=True, blank=True)
    member_system = models.ForeignKey('event_exim.EventSource', blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=75, null=True, blank=True)

    def __str__(self):
        return self.name or 'Activist {}:{}'.format(str(self.member_system), self.member_system_pk)

    def hash(self_or_email, email=None):
        """Should work as a class OR instance method"""
        if email is None:
            if hasattr(self_or_email, 'email'):
                email = getattr(self, 'email', None)
                if email is None:
                    raise Exception("You need to set the email or send it as an argument")
            else:
                email = self_or_email
        return hashlib.sha256(email.encode('utf-8')).hexdigest()

    def likely_same(self, other):
        eq_attrs = ('id', 'email', 'hashed_email', 'phone')
        for attr in eq_attrs:
            if getattr(self, attr) and getattr(self, attr)==getattr(other,attr,None):
                return True
        if self.member_system and self.member_system_pk\
           and self.member_system_id == getattr(other,'member_system_id', None)\
           and self.member_system_pk == getattr(other,'member_system_pk', None):
            return True
        return False


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

CHOICES = {
    'unknown': 0,
    #venues
    'private home': 1,
    'public space': 2,
    'target location (e.g. congressional district office)': 3,
    'virtual': 4,
    #ticket types
    'open': 1,
    'ticketed': 2,
    #is_private
    'public': 0,
    'private': 1,
    #is_searchable
    'not searchable': 0,
    'searchable': 1,
}

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
    venue = models.CharField(max_length=765, blank=True)
    phone = models.CharField(max_length=765, blank=True)
    public_description = models.TextField(blank=True)
    directions = models.TextField(blank=True)
    note_to_attendees = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    #from ground-control
    #eventIdObfuscated: {type: GraphQLString},
    organization_official_event = models.NullBooleanField(null=True)
    event_type = models.CharField(max_length=765, null=True, blank=True)
    organization_host = models.ForeignKey('Activist', blank=True, null=True)
    organization = models.ForeignKey('Organization', blank=True, null=True, db_index=True)
    organization_source = models.ForeignKey('event_exim.EventSource', blank=True, null=True, db_index=True)
    organization_campaign = models.CharField(max_length=765, db_index=True)
    organization_source_pk = models.CharField(max_length=765, blank=True, null=True, db_index=True)

    #this can be any other data the event source wants/needs to store
    # in this field to resolve additional information.  It can be the original data,
    # but could also be more extended info like social sharing data
    source_json_data = JSONField(null=True, blank=True)

    #hostId: {type: GraphQLString}, = add primary_host
    #localTimezone: {type: GraphQLString}, #not there, but starts_at + starts_at_utc sorta does that
    #duration: {type: GraphQLInt},
    is_searchable = models.IntegerField(choices=((0, 'not searchable'), (1, 'searchable')))
    private_phone = models.CharField(max_length=765, blank=True)
    
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
    ticket_type = models.IntegerField(choices=((0, 'unknown'), (1, 'open'), (2, 'ticketed')))
    share_url = models.URLField(blank=True)
    #share_options[] = facebook_share{title, desc, img}, twitter_share{msg}, email_share{subj,body}

    # See https://opencivicdata.readthedocs.io/en/latest/proposals/0002.html
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
    rsvp_url = models.URLField(blank=True, null=True)
    event_facebook_url = models.URLField(blank=True, null=True)
    organization_status_review = models.CharField(max_length=32, blank=True, null=True, db_index=True,
                                                  choices=EVENT_REVIEW_CHOICES)
    organization_status_prep = models.CharField(max_length=32, blank=True, null=True, db_index=True,
                                                choices=EVENT_PREP_CHOICES)

    #later
    def host_edit_url(self):
        pass #organization can implement

    def handle_rsvp(self):
        return None #organization can implement
