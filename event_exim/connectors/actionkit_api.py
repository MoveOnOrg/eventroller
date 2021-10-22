import datetime
from itertools import chain
import json
import re
from urllib.parse import quote as urlquote

from django.utils.html import format_html, mark_safe

from actionkit.api.event import AKEventAPI
from actionkit.api.user import AKUserAPI
from actionkit.utils import generate_akid
from event_store.models import Activist, Event, CHOICES

"""
Non-standard use in ActionKit:
* We assume a user field called "recent_phone" (because the phone table is a big pain)
* Custom Event Field mappings:
  - review_status
  - prep_status
  - needs_organizer_help
  - political_scope
  - public_phone
  - venue_category

"""

#MYSQL 2016-12-12 18:00:00
DATE_FMT = '%Y-%m-%d %H:%M:%S'

_LOGIN_TOKENS = {}


class AKAPI(AKUserAPI, AKEventAPI):
    #merge both user and event apis in one class
    pass


class Connector:
    """
    This connects to ActionKit with the rest api -- queries are done through
    ad-hoc report queries: https://roboticdogs.actionkit.com/docs/manual/api/rest/reports.html#running-an-ad-hoc-query
    which is inelegant compared with browsing /rest/v1/event/ however, we can't get all the fields
    we need from that one call, and it's currently impossible to sort by updated_at for easy syncing
    and it's very difficult to get the hosts without browsing all signups.  Better would be a
    way to filter eventsignups by role=host
    """

    description = ("ActionKit API connector that needs API- read-only access and API edit access"
                   " if you are going to save event status back")

    CAMPAIGNS_CACHE = {}
    USER_CACHE = {}

    #used for conversions
    date_fields = ('starts_at', 'ends_at', 'starts_at_utc', 'ends_at_utc', 'updated_at')

    common_fields = ['address1', 'address2',
                     'city', 'state', 'region', 'postal', 'zip', 'plus4', 'country',
                     'longitude', 'latitude',
                     'title', 'starts_at', 'ends_at', 'starts_at_utc', 'ends_at_utc', 'status', 'host_is_confirmed',
                     'is_private', 'is_approved', 'attendee_count', 'max_attendees',
                     'venue',
                     'public_description', 'directions', 'note_to_attendees',
                     'updated_at']

    other_fields = ['ee.id', 'ee.creator_id', 'ee.campaign_id', 'ee.phone', 'ee.notes', 'ec.name',
                    'ec.title', 'ee.us_district', 'signuppage.name', 'createpage.name',
                    'host.id', 'hostaction.id', 'hostaction2.action_ptr_id', 'hostcreateaction.action_ptr_id',
                    'u.id', 'u.first_name', 'u.last_name', 'u.email', 'loc.us_district', 'recentphone.value']

    event_fields = ['review_status', 'prep_status',
                    'needs_organizer_help', 'political_scope', 'public_phone', 'venue_category']

    #column indexes for the above fields
    field_indexes = {k: i for i, k in enumerate(
        common_fields
        + other_fields
        # this looks complicated, but just alternates between <field>, <field>_id for the eventfield id
        + list(chain(*[(ef, '%s_id' % ef) for ef in event_fields]))
    )}

    sql_query = (
        "SELECT %(commonfields)s, %(otherfields)s, %(eventfields)s"
        " FROM events_event ee"
        " JOIN events_campaign ec ON ee.campaign_id = ec.id"
        #host won't necessarily be unique but the GROUP BY will choose the first host signup
        " LEFT JOIN events_eventsignup host ON (host.event_id = ee.id AND host.role='host')"
        " LEFT JOIN core_user u ON (u.id = host.user_id)"
        " LEFT JOIN core_userfield recentphone ON (recentphone.parent_id = u.id AND recentphone.name = 'recent_phone')"
        " LEFT JOIN core_location loc ON (loc.user_id = u.id)"
        " JOIN core_eventsignuppage ces ON (ces.campaign_id = ee.campaign_id)"
        " JOIN core_page signuppage ON (signuppage.id = ces.page_ptr_id AND signuppage.hidden=0 AND signuppage.status='active')"
        " LEFT JOIN core_eventcreateaction hostcreateaction ON (hostcreateaction.event_id = ee.id)"
        " LEFT JOIN core_action hostaction ON (hostcreateaction.action_ptr_id = hostaction.id AND hostaction.user_id=host.user_id)"
        " LEFT JOIN core_eventsignupaction hostaction2 ON (hostaction2.signup_id = host.id)"
        " LEFT JOIN core_eventcreatepage cec ON (cec.campaign_id = ee.campaign_id)"
        " LEFT JOIN core_page createpage ON (createpage.id = cec.page_ptr_id AND createpage.hidden=0 AND createpage.status='active')"
        " %(eventjoins)s "
        " xxADDITIONAL_WHERExx "  # will be replaced with text or empty string on run
        # we need to include hostcreateaction in group by so it doesn't get squashed with first match
        " GROUP BY ee.id, host.id, hostcreateaction.action_ptr_id"
        " ORDER BY {{ ordering }} DESC"
        " LIMIT {{ max_results }}"
        " OFFSET {{ offset }}"
    ) % {'commonfields': ','.join(['ee.{}'.format(f) for f in common_fields]),
         'otherfields': ','.join(other_fields),
         'eventfields': ','.join(['{f}.value, {f}.id'.format(f=f) for f in event_fields]),
         'eventjoins': ' '.join([("LEFT JOIN events_eventfield {f}"
                                  " ON ({f}.parent_id=ee.id AND {f}.name = '{f}')"
                                  ).format(f=f) for f in event_fields]),
         }

    @classmethod
    def writable(cls):
        return True

    @classmethod
    def parameters(cls):
        return {'campaign': {'help_text': 'ID (a number) of campaign if just for a single campaign',
                             'required': False},
                'api_password': {'help_text': 'api password',
                                 'required': True},
                'api_user': {'help_text': 'api username',
                             'required': True},
                'max_event_load': {'help_text': ('The default number of events to back-load from'
                                                 ' the database. (if not set, then it will go'
                                                 'all the way back)'),
                                   'required': False},
                'base_url': {'help_text': 'base url like "https://roboticdocs.actionkit.com"',
                             'required': True},
                'allowed_hosts': {'help_text': ('defaults to base_url host, but if you have other'
                                                ' hosts that should be allowed to ping as the client'),
                                  'required': False},
                'ak_secret': {'help_text': 'actionkit "Secret" needed for auto-login tokens',
                              'required': False},
                'ignore_host_ids': {'help_text': ('if you want to ignore certain hosts'
                                                  ' (due to automation/admin status) add'
                                                  ' them as a json list of integers'),
                                    'required': False},
                'cohost_id': {'help_text': ('for easy Act-as-host links, if all events'
                                            ' have a cohost, then this will create'
                                            ' links that do not need ActionKit staff access'),
                              'required': False},
                'cohost_autocreate_page_id': {'help_text': ('If you want the cohost auto-added as a host'
                                                            'to all events add a page_id for event signup'),
                                              'required': False},

                }

    def __init__(self, event_source):
        self.source = event_source
        data = event_source.data

        self.base_url = data['base_url']

        class aksettings:
            AK_BASEURL = data['base_url']
            AK_USER = data['api_user']
            AK_PASSWORD = data['api_password']
            AK_SECRET = data.get('ak_secret')
        self.akapi = AKAPI(aksettings)
        self.ignore_hosts = set()
        if 'ignore_host_ids' in data:
            self.ignore_hosts = set([int(h) for h in data['ignore_host_ids'].split(',')
                                     if re.match(r'^\d+$', h)
                                     ])
        self.cohost_id = data.get('cohost_id')
        self.cohost_autocreate_page_id = data.get('cohost_autocreate_page_id')
        self._allowed_hosts = set(data['base_url'].split('/')[2])
        if data.get('allowed_hosts'):
            self._allowed_hosts.update(data['allowed_hosts'].split(','))

    def allowed_hosts(self):
        return self._allowed_hosts

    def _load_events_from_sql(self, ordering='ee.updated_at', max_results=10000, offset=0,
                              additional_where=[], additional_params={}):
        """
        With appropriate sql query gets all the events via report/run/sql api
        and returns None when there's an error or no events and returns
        a list of event row lists with column indexes described by self.field_indexes
        """
        if max_results > 10000:
            raise Exception("ActionKit doesn't permit adhoc sql queries > 10000 results")
        where_clause = ''
        if additional_where:
            where_clause = ' WHERE %s' % ' AND '.join(additional_where)
        query = {'query': self.sql_query.replace('xxADDITIONAL_WHERExx', where_clause),
                 'ordering': ordering,
                 'max_results': max_results,
                 'refresh': True,
                 'offset': offset}
        query.update(additional_params)
        res = self.akapi.client.post('{}/rest/v1/report/run/sql/'.format(self.base_url),
                                     json=query)
        if res.status_code == 200:
            return res.json()

    def _host2activist(self, host):
        """from dict out of _convert_host, into an activist model"""
        args = host.copy()
        args.pop('create_action')
        return Activist(member_system=self.source, **args)

    def _convert_host(self, event_row):
        fi = self.field_indexes
        return dict(member_system_pk=str(event_row[fi['u.id']]),
                    name='{} {}'.format(event_row[fi['u.first_name']], event_row[fi['u.last_name']]),
                    email=event_row[fi['u.email']],
                    hashed_email=Activist.hash(event_row[fi['u.email']]),
                    phone=event_row[fi['recentphone.value']],
                    #non Activist fields:
                    # we try hostaction2 -- a signup instead of create, first,
                    # because if there's a signup, there won't be a create
                    # however the create action will join on all events
                    # since the create action is just based on event_id, not the user
                    create_action=(event_row[fi['hostaction2.action_ptr_id']]
                                   or event_row[fi['hostaction.id']])
                    )

    def _convert_event(self, event_rows):
        """
        Based on a row from self.sql_query, returns a
        dict of fields that correspond directly to an event_store.models.Event object
        """
        event_row = event_rows[0]
        fi = self.field_indexes
        hackattempt = False

        def cleanchars(val, key):
            if isinstance(val, str):
                if key == 'state':
                    if not re.match(r'^[A-Z][A-Z]$', val.upper()):
                        # indication of corrupted state
                        hackattempt = True
                        return 'XX'
                    return val.upper()  # tx => TX
                if '\x00' in val:
                    hackattempt = True
                    # it would be nice to have a longer in-place message,
                    # but we don't want to break char-count maximums
                    return val.replace('\x00', 'X')
            return val
        event_fields = {k: cleanchars(event_row[fi[k]], k) for k in self.common_fields}
        signuppage = event_row[fi['signuppage.name']]
        campaign_slug = event_row[fi['ec.name']]
        e_id = event_row[fi['ee.id']]
        rsvp_url = (
            '{base}/event/{attend_page}/{event_id}/'.format(
                base=self.base_url, attend_page=signuppage, event_id=e_id)
            if signuppage else None)
        search_url = (
            '{base}/event/{attend_page}/search/'.format(
                base=self.base_url, attend_page=signuppage)
            if signuppage else None)
        slug = '{}-{}'.format(re.sub(r'\W', '', self.base_url.split('://')[1]), e_id)
        state, district = (event_row[fi['ee.us_district']] or '_').split('_')
        ocdep_location = ('ocd-division/country:us/state:{}/cd:{}'.format(state.lower(), district)
                          if state and district else None)

        # Now go through all the rows to get the different hosts
        hosts = {}
        main_host_id = None
        cohost_create_action = None
        for row in sorted(event_rows, key=lambda r: r[fi['host.id']]):
            host = self._convert_host(row)
            hostpk = int(host['member_system_pk'])
            if not main_host_id and hostpk not in self.ignore_hosts:
                main_host_id = hostpk
            # put the first one in hosts, and then only update
            #  if we have a create_action row
            if hostpk not in hosts or host.get('create_action'):
                hosts[hostpk] = host
            if hostpk == self.cohost_id:
                cohost_create_action = host['create_action']
        if self.cohost_autocreate_page_id \
           and self.cohost_id \
           and not cohost_create_action:
            # cohost has not been added yet -- let's add it
            res = self.akapi.create_signup(self.cohost_id,
                                           e_id,
                                           self.cohost_autocreate_page_id,
                                           role='host',
                                           fields={'source': 'automatic',
                                                   'provider': 'eventroller'})
            if res and res.get('id'):
                cohost_create_action = int(res['id'])

        event_fields.update({'organization_official_event': False,
                             'event_type': 'unknown',
                             'organization_host': (self._host2activist(hosts[main_host_id])
                                                   if main_host_id else None),
                             'organization_source': self.source,
                             'organization_source_pk': str(e_id),
                             'organization': self.source.origin_organization,
                             'organization_campaign': event_row[fi['ec.title']],
                             'is_searchable': (event_row[fi['status']] == 'active'
                                               and not event_row[fi['is_private']]),
                             'private_phone': event_row[fi['recentphone.value']] or '',
                             'phone': event_row[fi['public_phone']] or '',
                             'url': rsvp_url,  # could also link to search page with hash
                             'slug': slug,
                             'osdi_origin_system': self.base_url,
                             'ticket_type': CHOICES['open'],
                             'share_url': search_url,
                             'internal_notes': event_row[fi['ee.notes']],
                             #e.g. NC cong district 2 = "ocd-division/country:us/state:nc/cd:2"
                             'political_scope': (event_row[fi['political_scope']] or ocdep_location),
                             #'dupe_id': None, #no need to set it
                             'venue_category': CHOICES[event_row[fi['venue_category']] or 'unknown'],
                             'needs_organizer_help': event_row[fi['needs_organizer_help']] == 'needs_organizer_help',
                             'rsvp_url': rsvp_url,
                             'event_facebook_url': None,
                             'organization_status_review': event_row[fi['review_status']],
                             'organization_status_prep': event_row[fi['prep_status']],
                             'source_json_data': json.dumps({
                                 # other random data to keep around
                                 'campaign_id': event_row[fi['ee.campaign_id']],
                                 'create_page': event_row[fi['createpage.name']],
                                 'create_action_id': cohost_create_action,
                                 'hosts': hosts,
                                 'hack': hackattempt,
                                 'campaign_slug': campaign_slug,
                             }),
                             })
        for df in self.date_fields:
            if event_fields[df]:
                event_fields[df] = datetime.datetime.strptime(event_fields[df], DATE_FMT)
        return event_fields

    def get_event(self, event_id):
        """
        Returns an a dict with all event_store.Event model fields
        """
        events = self._load_events_from_sql(additional_where=['ee.id = {{event_id}}'],
                                            additional_params={'event_id': event_id})
        if events:
            return self._convert_event(events)

    def load_events(self, max_events=None, last_updated=None):
        additional_where = []
        additional_params = {}
        campaign = self.source.data.get('campaign')
        if campaign:
            additional_where.append('ee.campaign_id = {{ campaign_id }}')
            additional_params['campaign_id'] = campaign
        if last_updated:
            additional_where.append('ee.updated_at > {{ last_updated }}')
            additional_params['last_updated'] = last_updated
        # all_events keyed by id with values as a list of event_rows for the event
        # there can be multiple rows, at least because there can be multiple hosts
        all_events = {}
        max_events = max_events or self.source.data.get('max_event_load')
        event_count = 0
        for offset in range(0, max_events, min(10000, max_events)):
            if event_count > max_events:
                break
            events = self._load_events_from_sql(offset=offset,
                                                additional_where=additional_where,
                                                additional_params=additional_params,
                                                max_results=min(10000, max_events))
            if not events:
                break
            for event_row in events:
                e_id = event_row[self.field_indexes['ee.id']]
                if e_id in all_events:
                    all_events[e_id].append(event_row)
                else:
                    all_events[e_id] = [event_row]
                    event_count = event_count + 1
        return {'events': [self._convert_event(event_rows) for event_rows in all_events.values()],
                'last_updated': datetime.datetime.utcnow().strftime(DATE_FMT)}

    def update_review(self, event, reviews, log_message):
        res = self.akapi.get_event(event.organization_source_pk)
        if 'res' in res:
            eventfield_list = res['res'].json().get('fields', {})
            eventfields = {ef['name']: ef['id'] for ef in eventfield_list}
            for r in reviews:
                if r.key in ('review_status', 'prep_status'):
                    self.akapi.set_event_field(event.organization_source_pk,
                                               r.key, r.decision,
                                               eventfield_id=eventfields.get(r.key))

    def get_admin_event_link(self, event):
        if event.source_json_data:
            cid = json.loads(event.source_json_data).get('campaign_id')
            if cid:
                return '{}/admin/events/event/?campaign={cid}&event_id={eid}'.format(
                    self.base_url, cid=cid, eid=event.organization_source_pk)

    def get_host_event_link(self, event, edit_access=False, host_id=None, confirm=False):
        if event.status != 'active':
            return None
        jsondata = event.source_json_data
        create_page = None
        if jsondata:
            create_page = json.loads(jsondata).get('create_page')
        if not create_page:
            return None

        host_link = '/event/{create_page}/{event_id}/host/'.format(
            create_page=create_page,
            event_id=event.organization_source_pk)

        if not host_id:
            if self.cohost_id:
                host_id = self.cohost_id
            else:
                # no host to use.
                # maybe todo: use event host, but need to think of auth/consequences
                return None
        elif confirm:
            host_link = urlquote(host_link + '?confirmed=1')

        if edit_access and host_id and self.akapi.secret:
            #easy memoization for a single user
            token = _LOGIN_TOKENS.get(host_id, False)
            if token is False:
                token = self.akapi.login_token(host_id)
                _LOGIN_TOKENS[host_id] = token
            if token:
                host_link = '/login/?i={}&l=1&next={}'.format(token, host_link)
        return '{}{}'.format(self.base_url, host_link)

    def get_additional_hosts(self, event):
        additional_hosts = []
        if event.source_json_data:
            json_data = json.loads(event.source_json_data)
            hosts = json_data.get('hosts')
            if hosts:
                for hostpk, host in hosts.items():
                    if int(hostpk) not in self.ignore_hosts\
                       and (not event.organization_host_id
                            or hostpk != event.organization_host.member_system_pk):
                        additional_hosts.append(host)
        return additional_hosts

    def get_extra_event_management_html(self, event):
        additional_hosts = self.get_additional_hosts(event)

        def host_format(host):
            # glyphicon glyphicon-envelope
            # glyphicon glyphicon-earphone
            additional_info = []
            if host.get('email'):
                additional_info.append(format_html(
                    '<a href="mailto:{}"><span class="glyphicon glyphicon-envelope"></span></a>',
                    host['email']))
            if host.get('phone'):
                additional_info.append(format_html(
                    '<span class="glyphicon glyphicon-earphone"></span> {}',
                    Event.phone_format(host['phone'])))
            return format_html('<div data-pk="{}">{} {}</div>',
                               host['member_system_pk'],
                               host['name'],
                               mark_safe(' '.join(additional_info)))

        if additional_hosts:
            return mark_safe(
                '<div><b>Additional Hosts:</b>'
                + ''.join([host_format(h) for h in additional_hosts])
                + '</div>')
        return None
