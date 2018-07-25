import json

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.template.loader import render_to_string

from event_store.models import Event
from reviewer.views import reviewgroup_auth
from event_review.emails import send_messages

def adapt_event_to_email(message, event):
    src = event.organization_source
    host_link = src.api.get_host_event_link(event, edit_access=True,
                                            host_id=event.organization_host.member_system_pk,
                                            confirm=True)
    email_subject = 'Regarding your event with %s' % event.organization.title
    message = render_to_string(
        'event_review/message_to_host_email.html',
        {'host_name': event.organization_host.name,
         'event': event,
         'source': src.name,
         'link': host_link,
         'message': message,
         'footer': getattr(settings, 'EVENT_REVIEW_MESSAGE_FOOTER',
                           "\nThanks for all you do.")
     })
    return {
        'to': event.organization_host.email,
        'subject': email_subject,
        'message_text': message,
        'from_line': settings.FROM_EMAIL,
    }


@reviewgroup_auth
def send_host_message(request, organization, event_id, host_id=None):
    result = 'failed to send'

    if getattr(settings, 'FROM_EMAIL', None):
        event = Event.objects.filter(id=event_id).select_related('organization_host', 'organization').first()
        if event and event.organization_host_id and event.organization_host.email:
            src = event.organization_source
            if src and hasattr(src.api, 'get_host_event_link'):
                send_messages(request.POST.get('message',''),
                              [event],
                              adapt_event_to_email)
                result = 'success'

    response_json = json.dumps({
        'result': result,
    })
    return HttpResponse(response_json, content_type='application/json')
