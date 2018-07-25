from django.core.mail import get_connection as get_mail_connection
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string


def default_template_func(message, obj):
    return {
        'to': obj.email,
        'subject': 'Message about {}'.format(str(obj)), # TODO? should we make it a setting?
        'message_text': message, # TODO? wrap in minimal template?
        'from_line': settings.FROM_EMAIL,
    }

def send_messages(message, objects, template_func=default_template_func, actually_send=True):
    """
    1. create EmailMessage objects using template_func as an adapter/transformer to objects
    2. save message to object (in reviewlog or contactmessage thingie
    3. send the messages
    It will not check access control
    """
    connection = get_mail_connection()
    messages = []
    for obj in objects:
        message_dict = template_func(message, obj)
        messages.append(create_message(**message_dict))
    if actually_send:
        self.connection.send_messages(messages)
    # TODO: save messages into reviewlog or similar
    return messages

    
def create_message(to=None, subject=None, message_text=None, message_html='',
                   from_line=None, from_name=None, from_email=None,
                   reply_to=None, headers=None,
                   actually_send=False, **kwargs):
    extra_args = {}
    if reply_to:
        extra_args['reply_to'] = [reply_to]  # EmailMultiAlternatives takes a list
    if headers:
        extra_args['headers'] = headers
    if not from_line and from_name and from_email:
        from_line = '"{}" <{}>'.format(from_name.replace('"', '\\"'), from_email)
    mailmessage = EmailMultiAlternatives(subject, message_text, from_line, [to],
                                         **extra_args)
    if message_html:
        mailmessage.attach_alternative(message_html, "text/html")
    # This is inefficient. Use a petitions/queues.py EmailProcessor to send even
    # transactional messages faster
    if actually_send:
        mailmessage.send(fail_silently=True)
    return mailmessage
