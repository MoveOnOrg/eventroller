import datetime
from itertools import chain
import json
import re
import time

import requests
from event_store.models import Activist, CHOICES

#facebook wants php strtotime() format
# https://secure.php.net/manual/en/function.strtotime.php
DATE_FMT = '%Y-%m-%dT%H:%M:%S%z'

def strip_tz(datetime):
    """Strip the timezone for USE_TZ=False"""
    return datetime.replace(tzinfo=None)

class Connector:
    """

    """

    description = """
[Updated 7/18/2017]
1. Create a Facebook account.
2. Go to [Facebook for Developers](developers.facebook.com). Click on the blue *Get Started* button in the top-right corner. Create a *New App ID*. Any name will do. We recommend `eventroller`.
3. Get a long-lived user access token:
    * Go to [Facebook's Graph API Explorer](https://developers.facebook.com/tools/explorer). Look for the top right dropdown. It should have a Label saying *Application*, and a value of *Graph API Explorer*. Click on the dropdown and change it it to your app.
    * Under the *Get Token* dropdown, click on *Get User Access Token*. A modal should popup. There, select `user_events` and `pages_show_list` as permissions. Then click on *Get Access Token*. (Facebook may ask for additional permissions at this point. Click yes.)
    * Under the *Get Token* dropdown, click on *Page Access Tokens*. (Don't accidently click on *Get App Token*. That will replace your User Access Token with an App Token. We want the Page Access Token to build on top of the User Access Token. If you lose the User Access Token, then repeat the previous step before proceeding with this one.)
    * Click the little blue i left of the Token. A box should popup with token information. Note the expiration time, then click *Open in Access Token Tool*.
    * Click the blue *Extend Access Token* button at the bottom of the page. A new Access Token should pop up at the bottom.
    * Click the white "Debug" button to the right. "Expires" should show a date two months into the future.
4. Create a `./local_settings.py` file in your root directory if you don't have one. Save this Access Token as an `auth_token` property on a facebook app. (See `local_settings.py.example` for a guide.)
5. Go to your app dashboard from [All Apps - Facebook for Developers](developers.facebook.com/apps). Copy the *App ID* and *App Secret* into `app_id` and `app_secret` properties on a facebook app. (See `local_settings.py.example` for a guide.)
    """

    # See https://developers.facebook.com/docs/graph-api/reference/event/
    EVENT_FIELDS = ['id',
                    'name', #= title
                    'start_time', #format: 2017-04-06T10:00:00-0400
                    'end_time',
                    'description',
                    'type',
                    'category',
                    'ticket_uri', #not nec avail
                    'cover.fields(id,source)', #source is url
                    'picture.type(large)', #picture.data.url
                    'attending_count',
                    'declined_count',
                    'maybe_count',
                    'noreply_count',
                    'can_guests_invite',
                    'can_viewer_post',
                    'interested_count',
                    'is_canceled',
                    'is_draft',
                    'is_page_owned',
                    'is_viewer_admin',
                    'owner',
                    'parent_group',
                    # place might just get place.name (which could include
                    # full address with city/state/zip as one string)
                    ('place.location(city,'
                     'country_code,latitude,longitude,'
                     'name,region,state,street,zip)'),
                    'timezone', # e.g. "America/New_York"
                    'updated_time', #format: 2017-05-04T14:48:21+0000
                    'ticketing_privacy_uri',
                    'ticketing_terms_uri',
                ]

    PAGE_FIELDS = ['id',
                   'name',
                   'cover.fields(id,source)',
                   'picture.type(large)',
                   'location',
                   'category', #e.g. 'Nonprofit Organization'
                   'link']

    @classmethod
    def writable(cls):
        return False

    @classmethod
    def parameters(cls):
        return {'app_id': {'help_text': 'app_id',
                           'required': True},
                'app_secret': {'help_text': 'app_secret',
                               'required': True},
                'auth_token': {'help_text': 'auth token -- will acquire one if not supplied',
                               'required': True},
                'token_expires': {'help_text': 'date in "2017-08-08" format for when the authtoken expires',
                                  'required': False},
                #either page_ids or event_ids is required to load_events automatically
                'page_ids': {'help_text': ('page id (your facebook url after the first'
                                           ' /, e.g. https://www.facebook.com/moveon/'
                                           ' => "moveon" for page_id)'
                                           ' For multiple, separate by commas.'),
                             'required': False},
                'event_ids': {'help_text': ('event ids are the url after'
                                            '"facebook.com/event/"'
                                            ' This should be a comma separated list for multiple.'),
                             'required': False},
                'max_paging': {'help_text': 'how many pages (of 25) to iterate back through (default is 10).',
                               'required': False}
        }

    def __init__(self, event_source):
        self.source = event_source
        data = event_source.data

        self.base_url = 'https://graph.facebook.com/'
        self.api_version = 'v2.9/'
        self.auth_token = data.get('auth_token')
        self.page_ids = data.get('page_ids')
        self.event_ids = data.get('event_ids')
        self.max_paging = data.get('max_paging', 10)

    def _convert_host(self, facebook_event):
        owner = facebook_event.get('owner', {})
        if owner:
            return Activist(member_system=self.source,
                            member_system_pk=owner.get('id'),
                            name=owner.get('name'))
        else:
            return None

    def _convert_event(self, facebook_event):
        start_time = datetime.datetime.strptime(facebook_event['start_time'], DATE_FMT)
        end_time = (datetime.datetime.strptime(facebook_event['end_time'], DATE_FMT)
                    if facebook_event.get('end_time') else None)
        # TODO: sometimes place.name will have a full address on one line without it broken down into location
        location = facebook_event.get('place',{}).get('location', {})
        is_private = 1 if (facebook_event.get('is_draft')  or facebook_event['type'] != 'public') else 0
        url = 'https://www.facebook.com/events/{}'.format(facebook_event['id'])
        TODO = None
        event_fields = {
            'address1': location.get('street'),
            'address2': None,
            'city': location.get('city'),
            'state': location.get('state'),
            'region': location.get('region', location.get('state')),
            'postal': location.get('zip'), #TODO: need international example
            'zip': location.get('zip'),
            'plus4': None,
            'country': location.get('country'), #"United States"
            'longitude': location.get('longitude'),
            'latitude': location.get('latitude'),
            'title': facebook_event['name'],
            'starts_at_utc': strip_tz(datetime.datetime.fromtimestamp(
                                time.mktime(start_time.utctimetuple()))),
            'ends_at_utc': (strip_tz(datetime.datetime.fromtimestamp(
                                time.mktime(end_time.utctimetuple())))
                            if end_time else None),
            'starts_at': strip_tz(start_time),
            'ends_at': strip_tz(end_time),
            # yes, facebook spells is 'canceled' (and eventstore/actionkit spell it 'cancelled'
            'status': 'cancelled' if facebook_event.get('is_canceled') else 'active',
            'host_is_confirmed': 1, # facebook claims to makes sure accounts are people
            'is_private': is_private,
            'is_approved': 1,
            'attendee_count': facebook_event.get('attending_count'),
            'max_attendees': None,
            'venue': facebook_event.get('place',{}).get('name',''),
            'public_description': facebook_event['description'],
            'directions': '',
            'note_to_attendees': '',
            'updated_at': datetime.datetime.strptime(facebook_event['updated_time'], DATE_FMT),
            'organization_official_event': TODO, # maybe if same org as page or is_owner
            'event_type': facebook_event.get('category'), # "EVENT_CAUSE", "CAUSES", "OTHER"
            'organization_host': self._convert_host(facebook_event), #TODO
            'organization_source': self.source,
            'organization_source_pk': facebook_event['id'],
            'organization': self.source.origin_organization,
            'organization_campaign': '', # maybe owner?
            'is_searchable': not is_private,
            'private_phone': '',
            'phone': '',
            'url': url,
            'slug': 'facebook-{}'.format(facebook_event['id']),
            'osdi_origin_system': 'facebook.com',
            # unknown unless we have a ticket uri
            'ticket_type': (CHOICES['ticketed']
                            if facebook_event.get('ticket_uri')
                            else CHOICES['unknown']),
            'share_url': url,
            'internal_notes': '',
            #e.g. NC cong district 2 = "ocd-division/country:us/state:nc/cd:2"
            'political_scope': None, #TODO: zip2district support
            'venue_category': CHOICES['unknown'],
            'needs_organizer_help': 0,
            'rsvp_url': facebook_event.get('ticket_uri', url),
            'event_facebook_url': url,
            'organization_status_review': None,
            'organization_status_prep': None,
            'source_json_data': json.dumps({
                k:facebook_event.get(k)
                for k in ('maybe_count',
                          'interested_count',
                          'declined_count',
                          'parent_group',
                          'timezone',
                          'ticketing_privacy_uri',
                          'ticketing_terms_uri',
                          'is_viewer_admin',
                          'can_viewer_post',
                          'owner')
            }),
        }
        return event_fields


    def _api_load(self, ids, ids_are_events=True,
                  since_str='', follow_next=None):
        """
        Load a list of events from facebook api.
        if `ids` are comma-separated events, then ids_are_events=True
        if `ids` are comma-separated pages, then ids_are_events=False
        """
        ids = re.sub(r'[^\w,-]', '', ids) # securiteh!
        if follow_next is None:
            follow_next = self.max_paging
        params = {"ids": ids,
                  "access_token": self.auth_token}
        fieldlist = ','.join(self.EVENT_FIELDS)

        if ids_are_events:
            params['fields'] = fieldlist
        else: #they must be pages
            params['fields'] = "events.fields({0}){1}".format(
                fieldlist, since_str)
        res = requests.get('{}{}'.format(
            self.base_url, self.api_version), params=params)
        events = res.json()
        # pages return arrays (under events.data)
        # events return the event object directly
        # so we homogenize the output to a single list
        # TODO: maybe the PAGE should be campaign or maybe page=owner?
        if ids_are_events:
            return list(events.values())
        else:
            fb_events = []
            for page_id, result in events.items():
                fb_events.extend(result.get('events',{}).get('data',[]))
                next_link = result.get('events',{}).get('paging',{}).get('next')
                while next_link and follow_next > 0:
                    events = requests.get(next_link).json()
                    fb_events.extend(events.get('data',[]))
                    next_link = result.get('paging',{}).get('next')
                    follow_next = follow_next - 1
            return fb_events

    def get_event(self, event_id_or_url):
        """
        Returns an a dict with all event_store.Event model fields
        """
        is_url = re.match(r'https://www.facebook.com/events/(\d+)', event_id_or_url)
        if is_url:
            event_id_or_url = is_url.group(1)
        events = self._api_load(event_id_or_url, ids_are_events=True)
        if events:
            return self._convert_event(events[0])

    def load_events(self, max_events=None, last_updated=None):
        all_events = []

        since_str = ''
        if last_updated:
            since_str = '.since({1})'.format(last_updated)

        if self.event_ids:
            events = self._api_load(self.event_ids, ids_are_events=True)
            all_events.extend([self._convert_event(e) for e in events])
        if self.page_ids:
            events = self._api_load(self.page_ids, ids_are_events=False,
                                    since_str=since_str)
            all_events.extend([self._convert_event(e) for e in events])

        return {'events': all_events,
                'last_updated': datetime.datetime.utcnow().strftime(DATE_FMT)}
