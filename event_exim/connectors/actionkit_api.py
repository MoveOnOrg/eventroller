import re

from actionkit.api.event import AKEventAPI
from actionkit.api.user import AKUserAPI
from event_store.models import Activist, Event

"""
Non-standard use in ActionKit:
* We assume a user field called "recent_phone" (because the phone table is a big pain)
* Custom Event Field mappings:
  review_status
  prep_status


"""


class AKAPI(AKUserAPI, AKEventAPI):
    #merge both user and event apis in one class
    pass

class Connector:

    CAMPAIGNS_CACHE = {}
    HOSTS_CACHE = {}

    common_fields = ('address1', 'address2',
                     'city', 'state', 'region', 'postal', 'zip', 'plus4', 'country',
                     'longitude', 'latitude',
                     'title', 'starts_at', 'ends_at', 'starts_at_utc', 'ends_at_utc', 'status', 'host_is_confirmed',
                     'is_private', 'is_approved', 'attendee_count', 'max_attendees',
                     'venue',
                     'public_description', 'directions', 'note_to_attendees', 'notes',
                     'updated_at')

    event_fields = set(['review_status', 'prep_status',
                        'needs_organizer_help', 'political_scope', 'public_phone', 'venue_category'])

    @classmethod
    def writable(cls):
        return True

    @classmethod
    def parameters(cls):
        return {'campaign': {'help_text': 'ID (a number) of campaign if just for a single campaign'
                             'required': False},
                'api_password': {'help_text': 'api password',
                            'required': True},
                'api_user': {'help_text': 'api username',
                             'required': True},
                'max_event_load': {'help_text': 'The default number of events to back-load from the database.  (if not set, then it will go all the way back)',
                                   'required': False},
                'base_url': {'help_text': 'base url like "https://roboticdocs.actionkit.com"',
                                  'required': True},
                'ak_secret': {'help_text': 'actionkit "Secret" needed for auto-login tokens',
                              'required': False},
                'ignore_host_ids': {'help_text': ('if you want to ignore certain hosts'
                                                  ' (due to automation/admin status) add'
                                                  ' them as a comma separated list'),
                                    'required': False}
        }

    def __init__(self, event_source):
        self.source = event_source
        self.base_url = data['base_url']
        data = event_source.data
        class aksettings:
            AK_BASEURL = data['base_url']
            AK_USER = data['api_user']
            AK_PASSWORD = data['api_password']
            AK_SECRET = data.get('ak_secret')
        self.akapi = AKAPI(aksettings)
        self.ignore_hosts = data['ignore_host_ids'] if 'ignore_host_ids' in data else []

    def _load_campaign(self, campaign_path):
        """campaign_path will be in the form /rest/v1/campaign/<ID>/"""
        if campaign_path in self.CAMPAIGNS_CACHE:
            return self.CAMPAIGNS_CACHE[campaign_path]
        res = self.akapi.client.get('{}{}'.format(self.base_url, campaign_path))
        if res.status == 200:
            c = res.json()
            if c.get('eventsignuppages'):
                signup = self.akapi.client.get('{}{}'.format(
                    self.base_url, c['eventsignuppages'][0]))
                if signup.status == 200:
                    c['_SIGNUPPAGE'] = signup.json()
            self.CAMPAIGNS_CACHE[campaign_path] = c
        else:
            #so we don't keep trying the same failing path
            self.CAMPAIGNS_CACHE[campaign_path] = None
        return self.CAMPAIGNS_CACHE[campaign_path]

    def _load_host(self, user_url):
        """
        Sends host,location_string tuple back, from api+local database
        """
        if user_url in self.USER_CACHE:
            return self.USER_CACHE[user_url]
        try:
            user = self.akapi.client.get('{}{}'.format(self.base_url, user_url)).json()
            host, created = Activist.objects.get_or_create(
                member_system=self.source,
                member_system_id=user['id'],
                defaults={'name': '{} {}'.format(user['first_name'], user['last_name']),
                          'email': user['email'],
                          'hashed_email': Activist.hash(user['email']),
                          'phone': user['fields'].get('recent_phone')})
            ocdep_str = None
            if user['zip']:
                location = self.akapi.client.get('{}/rest/v1/location/{}'.format(self.base_url, user['id']))
                if location.status == 200:
                    district = location.json()['us_district']
                    if district:
                        state, dist = district.split('_')
                        ocdep_str = 'ocd-division/country:us/state:{}/cd:{}'.format(state.lower(), dist)
            self.USER_CACHE[user_url] = (host, ocdep_str)
            return self.USER_CACHE[user_url]
        except:
            return (None, None)

    def _convert_event(self, ak_event_json):
        kwargs = {k:ak_event_json.get(k) for k in self.common_fields}
        evt = Event(**kwargs)
        campaign = self._load_campaign(ak_event_json['campaign'])
        rsvp_url = None
        search_url = None
        if campaign and '_SIGNUPPAGE' in campaign:
            rsvp_url = '{base}/event/{attend_page}/{event_id}/'.format(
                base=self.base_url,
                attend_page=campaign['_SIGNUPPAGE']['name'],
                event_id=ak_event_json['id'])
            search_url = '{base}/event/{attend_page}/search/'.format(
                base=self.base_url,
                attend_page=campaign['_SIGNUPPAGE']['name'])
        slug = '{}-{}'.format(re.sub(r'\W', '', self.base_url.split('://')[1]),
                              ak_event_json['id'])
        eventfields = {}
        host, ocdep_location = self._load_host(ak_event_json['creator'])
        for eventfield in ak_event_json['fields']:
            if eventfield['name'] in self.event_fields:
                eventfields[eventfield['name']] = eventfield['value']
        more_data = {'organization_official_event': False,
                     'event_type': 'unknown',
                     'organization_host': host,
                     'organization_source': self.source,
                     'organization_source_id': ak_event_json['id'],
                     'organization' self.source.origin_organization,
                     'organization_campaign': self.campaign.get('title'),
                     'is_searchable': (ak_event_json['status'] == 'active'
                                       and not ak_event_json['is_private']),
                     'private_phone': ak_event_json.get('phone'),
                     'phone': eventfields.get('public_phone', ''),
                     'url': rsvp_url, #could also link to search page with hash
                     'slug': slug,
                     'osdi_origin_system': self.base_url,
                     'ticket_type': 'open',
                     'share_url': search_url,
                     #e.g. NC cong district 2 = "ocd-division/country:us/state:nc/cd:2"
                     'political_scope': eventfields.get('political_scope', ocdep_location),
                     #'dupe_id': None, #no need to set it
                     'venue_category': eventfields.get('political_scope', 'unknown'),
                     #TODO: if host_ids are only hosts, then yes, but we need a better way to filter role=host signups
                     'needs_organizer_help': eventfields.get('needs_organizer_help') == 'needs_organizer_help',
                     'rsvp_url': rsvp_url,
                     'event_facebook_url': None,
                     'organization_status_review': eventfields.get('review_status'),
                     'organization_status_prep': eventfields.get('prep_status'),
        }
        for k,v in more_data.items():
            setattr(evt, k, v)
        return evt
        

    def get_event(self, event_id):
        """
        Returns an (unsaved) event_store.Event model object with an (ActionKit/vendor) event_id
        """
        res = self.akapi.get_event(event_id)
        if 'res' in res:
            return self._convert_event(res['res'].json())
        return None

    def update_event(self, event):
        pass

    def look_for_new_events(self):
        # note that the event_source object will have a 'last updated' value
        pass
        
    def load_all_events(self):
        next_url = '/rest/v1/event/?order_by=-id'
        campaign = self.source.data.get('campaign')
        if campaign:
            next_url = '{}&campaign={}'.format(next_url, campaign)
        all_events = []
        max_events = self.source.data.get('max_event_load')
        event_count = 0
        while next_url and (not max_events or event_count < max_events):
            res = self.akapi.client.get('{}{}'.format(self.base_url, next_url))
            if res.status != 200:
                next_url = None
            else:
                events = res.json()
                next_url = events['meta'].get('next')
                for e_json in events.get('objects', []):
                    event_count = event_count + 1
                    all_events.append(self._convert_event(e_json)
        return all_events

    def update_review(self, review):
        pass

    def get_host_event_link(self, event):
        #might include a temporary token
        pass
