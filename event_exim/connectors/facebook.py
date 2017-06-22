import datetime
from itertools import chain
import json
import re
import time

import requests

#facebook wants php strtotime() format
# https://secure.php.net/manual/en/function.strtotime.php
DATE_FMT = '%Y-%m-%dT%H:%M:%S%z'

class Connector:
    """
    
    """

    description = """
1. Create a facebook app, then add Events capability to it -- you don't have to submit it.
2. Get a long-lived user access token:
    * Go to [Facebook's Graph API Explorer](https://developers.facebook.com/tools/explorer) and
      make sure it is associated with your app (top right drop down).
    * Under Get Token, choose Get User Access Token, ensuring `user_events` and `pages_show_list`
      (and maybe `rsvp_event`) are both selected as permissions.
    * Under Get Token > Page Access Tokens, chose your target Page.
    * Click the little blue i to the left of the Token and note the expiration time. Choose Open in Access Token Tool.
    * Click the blue Extend Access Token button at the bottom of the page. The Access Token toward the top of the page 
should change.
    * Click the "Debug" button to the right. "Expires" should show "Never"
3. The Ad Account ID is a large integer displayed in several places in the business.facebook.com interface.
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
                    'timezone',
                    'updated_time', #format: 2017-05-04T14:48:21+0000
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
                'page_id': {'help_text': ('page id (your facebook url after the first'
                                          ' /, e.g. https://www.facebook.com/moveon/'
                                          ' => "moveon" for page_id)'),
                            required: True},
        }

    def __init__(self, event_source):
        self.source = event_source
        data = event_source.data

        self.base_url = 'https://graph.facebook.com/'
        self.api_version = 'v2.9/'
        self.auth_token = data.get('auth_token')
        self.page_id = data['page_id']

    def _convert_host(self, facebook_event):
        return None #TODO

    def _convert_event(self, facebook_event):
        start_time = datetime.datetime.strptime(facebook_event['start_time'], DATE_FMT)
        end_time = (datetime.datetime.strptime(facebook_event['end_time'], DATE_FMT)
                    if facebook_event.get('end_time') else None)
        TODO = None
        event_fields = {
            'address1': TODO,
            'address2': TODO,
            'city': TODO,
            'state': TODO,
            'region': TODO,
            'postal': TODO,
            'zip': TODO,
            'plus4': TODO,
            'country': TODO,
            'longitude': TODO,
            'latitude': TODO,
            'title': facebook_event['name'],
            'starts_at': start_time,
            'ends_at': end_time,
            'starts_at_utc': datetime.datetime.fromtimestamp(time.mktime(start_time.utctimetuple())),
            'ends_at_utc': (datetime.datetime.fromtimestamp(time.mktime(end_time.utctimetuple()))
                            if end_time else None),
            'status': TODO,
            'host_is_confirmed': 1, # facebook claims to makes sure accounts are people
            'is_private': facebook_event['is_draft'],
            'is_approved': 1,
            'attendee_count': TODO,
            'max_attendees': TODO,
            'venue': TODO,
            'public_description': facebook_event['description'],
            'directions': TODO,
            'note_to_attendees': TODO,
            'updated_at': TODO,
            'organization_official_event': TODO, #maybe if same org as page or is_owner
            'event_type': TODO, #'unknown',
            'organization_host': self._convert_host(facebook_event), #TODO
            'organization_source': self.source,
            'organization_source_pk': facebook_event['id'],
            'organization': self.source.origin_organization,
            'organization_campaign': TODO,
            'is_searchable': TODO
            'private_phone': '',
            'phone': '',
            'url': TODO,
            'slug': TODO,
            'osdi_origin_system': TODO,
            'ticket_type': TODO,
            'share_url': TODO,
            'internal_notes': '',
            #e.g. NC cong district 2 = "ocd-division/country:us/state:nc/cd:2"
            'political_scope': TODO,
            'venue_category': TODO,
            'needs_organizer_help': TODO,
            'rsvp_url': TODO,
            'event_facebook_url': TODO,
            'organization_status_review': None,
            'organization_status_prep': None,
            'source_json_data': None,
        }
        return event_fields


    def get_owner(self, owner_id):
        """
        {'id': '14226615647', 'link': 'https://www.facebook.com/peoplefor/', 'name': 'People For the American Way', 'location': {'zip': '20005', 'country': 'United States', 'state': 'DC', 'latitude': 38.90411, 'city': 'Washington', 'longitude': -77.0342, 'street': '1101 15th St NW Ste 600'}, 'category': 'Nonprofit Organization'}
        owner_json = requests.get(
            '{}{}{}'.format(self.base_url, self.api_version),
        """
        pass

    def get_event(self, event_id):
        """
        Returns an a dict with all event_store.Event model fields
        """
        pass

    def load_events(self, max_events=None, last_updated=None):
        all_events = []

        since_str = ''
        if last_updated:
            since_str = '.since({1})'.format(last_updated)

        page_sanitized = re.sub(r'\W', '', self.page_id) # securiteh!
        #TODO: loop through next links
        events = requests.get(
            '{}{}'.format(self.base_url, self.api_version),
            params={
                "ids": page_sanitized,
                "fields": "events.fields({0}){1}".format(
                    ','.join(self.EVENT_FIELDS), since_str),
                "access_token": self.auth_token,
            }).json()
        result = events.get(page_sanitized)
        if result:
            event_data = result['events']['data']
        else:
            print('failed result')
        import pdb; pdb.set_trace()
        return {'events': all_events,
                'last_updated': datetime.datetime.utcnow().strftime(DATE_FMT)}
