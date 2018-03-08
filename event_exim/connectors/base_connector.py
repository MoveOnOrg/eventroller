"""
This is a template for writing a connector.
We should make documentation for that in docs/ and reference this file.
"""


class Connector:

    description = "Big description of what and how the connector does for a user"

    @classmethod
    def writable(cls):
        return False # unless you support writing back fields

    @classmethod
    def parameters(cls):
        return {'config_option_1': {'help_text': 'either a username/token/password',
                                    'required': True},
                'config_option_2': {'help_text': 'This text describes the option',
                                    'required': False},}

    def __init__(self, event_source):
        # the top event source that is using this connector
        self.source = event_source
        # all the data defined by parameters that is needed to config this connector
        # and connect to the event system
        self.parameter_data = event_source.data

    def get_event(self, event_id):
        """
        event_id can be a number or a url, etc -- whatever the event system
        considers a primary key.  It should be what's returned in the
        field/key 'organization_source_pk'
        """
        raise NotImplementedError("get_event not implemented")
        return {
            # return a dict with all the fields for event_store.models.Event
            # 'organization_host' should be a dict with the event_store.models.Activist fields
        }

    def load_events(self, max_events=None, last_updated=None):
        raise NotImplementedError("get_event not implemented")
        return {
            'events': [
                # event dicts exactly like what is sent with get_event()
            ],
            'last_updated': 'some string that is useful for tracking the previous last-update moment'}

    #def update_review(self, event, reviews, log_message):
    #    """
    #    optional to be implemented.  If you don't implement it, don't include this function
    #    arguments are event_store.models.Event, reviewer.models.Review(s), and 
    #    log_message is a text message for the comment
    #    """
    #    pass

    #def get_admin_event_link(self, event):
    #    optional method to provide a link for event system 'admins'

    #def get_host_event_link(self, event, edit_access=False, host_id=None, confirm=False):
    #    optional method to provide a link for the host

    #def get_extra_event_management_html(self, event):
    #    optional method to provide additional html for reviewers per-event

    #def send_events(self, events, force_create=False):
    #    """
    #    @event event_object (not necessarily saved, so event.id may not exist)
    #    @force_create can force a new event, even if organization_source_pk
    #    @return any event dict keys that are 'new' or should be updated
    #            (especially organization_source_pk)
    #    """
