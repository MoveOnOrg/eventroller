import json

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string

from actionkit.api.user import AKUserAPI
from event_store.models import Event
from event_exim.connectors.actionkit_api import Connector

def send_actionkit_host_login_reminder(request, event_id):
    result = 'failed to send'

    if settings.FROM_EMAIL:
        event = Event.objects.filter(id=event_id).first()
        if event:
            src = event.organization_source
            if src and hasattr(src.api, 'get_host_event_link'):
                host_link = src.api.get_host_event_link(event, edit_access=True, host_id=event.organization_host.member_system_pk)
                email_subject = '%s Event Host Login Link' % src.name
                message = message = render_to_string(
                    'event_review/email-actionkit_host_login.html',
                    {'host_name': event.organization_host.name,
                     'source': src.name,
                     'link': host_link})
                mailmessage = EmailMultiAlternatives(email_subject, message, settings.FROM_EMAIL, [event.organization_host.email])
                mailmessage.send()
                result = 'success'

    response_json = json.dumps({
        'result': result,
    })
    return HttpResponse(response_json, content_type='application/json')
