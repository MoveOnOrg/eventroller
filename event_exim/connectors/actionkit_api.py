from actionkit.api.event import AKEventAPI
from event_store.models import Event

class Connector:

    @classmethod
    def writable(cls):
        return True

    @classmethod
    def parameters(cls):
        return {'campaign': {'help_text': 'ID of campaign if just for a single campaign'
                             'required': False},
                'api_password': {'help_text': 'api password',
                            'required': True},
                'api_user': {'help_text': 'api username',
                             'required': True},
                'actionkit url': {'help_text': 'base url like "https://roboticdocs.actionkit.com"',
                                  'required': True},
                'ak_secret': {'help_text': 'actionkit "Secret" needed for auto-login tokens',
                              'required': False}
        }

    def __init__(self, event_source):
        self.source = event_source
        data = event_source.data
        class aksettings:
            AK_BASEURL = data['base_url']
            AK_USER = data['api_user']
            AK_PASSWORD = data['api_password']
            AK_SECRET = data.get('ak_secret')
        self.akapi = AKEventAPI(aksettings)

    def get_event(self, event_id):
        """
        Returns an (unsaved) event_store.Event model object with an (ActionKit/vendor) event_id
        """
        self.akapi.get_event(event_id)
        return Event()

    def update_event(self, event):
        pass

    def look_for_new_events(self):
        # note that the event_source object will have a 'last updated' value
        pass

    def load_all_events(self):
        # https://act.moveon.org/rest/v1/event/?order_by=-id&campaign=82
        # https://act.moveon.org/rest/v1/eventsignup/?order_by=-id&event__campaign=82
        # https://act.moveon.org/rest/v1/campaign/82/
        # https://act.moveon.org/rest/v1/campaign/?order_by=-id
        pass

    def update_event_review(self, review):
        pass

    def get_host_event_link(self, event):
        #might include a temporary token
        pass
