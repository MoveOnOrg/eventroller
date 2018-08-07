import random

from django.core.mail import get_connection as get_mail_connection
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.core.mail import send_mail, EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe

from reviewer.models import ReviewGroup, ReviewLog

class MessageSendingAdminMixin:
    """
    How to wire this up:
    * Add as a mixin to your admin class, e.g. `class FooAdmin(MessageSendingAdminMixin, admin.ModelAdmin):...`
    * In list_display, add 'send_message_widget'
      - You can also add it to your fields or fieldset or get_fields....
    * add 'send_message_action' to actions, or get_actions to allow for sending a message to many at once

    Things to possibly override:
    * message_send_ready: If there are other things to mark when sending is possible
      - This could be added permission testing, or based on settings, etc.
    * message_obj_lookup: If the object
      - You can also use this if there are tests on the object itself that
        will mark it not sendable -- if something is not sendable return None
    * obj2orgslug: If there is a different way to derive the organization (slug) then use this
      - For particular admin interfaces you might, e.g. want to hardcode the organization
    * message_template: Customize the email content that goes out from the message and the object
    """
    send_a_message_placeholder = 'Send a message'
    # something to track the organization, to send options for visibility
    review_organization_filter = None

    def send_message_path(self):
        return '{app_label}_{model_name}_send_message'.format(
            app_label=self.model._meta.app_label,
            model_name=self.model._meta.model_name)

    def get_urls(self):
        urls = admin.ModelAdmin.get_urls(self)
        my_urls = [
            url('send_message/(?P<organization>[-.\w]+)/(?P<obj_id>[-.\w]+)/',
                self.admin_site.admin_view(self.send_message),
                name=self.send_message_path())
        ]
        return urls + my_urls

    def send_message(self, request, organization, obj_id):
        self.user = request.user
        result = 'failed to send'
        if not ReviewGroup.user_allowed(request.user, organization):
            result = 'permission denied'
        elif request.method == 'POST' and self.message_send_ready():
            obj = self.message_obj_lookup(obj_id, organization, request)
            if obj:
                self.send_messages(request.POST.get('message',''), [obj],
                                   visibility=request.POST.get('visibility'))
                result = 'success'
        response_json = json.dumps({'result': result})
        return HttpResponse(response_json, content_type='application/json')

    def message_send_ready(self, organization, request):
        return getattr(settings, 'FROM_EMAIL', None)

    def message_obj_lookup(self, obj_id, organization, request):
        """
        Used to lookup the object, and verify that the system has everything it needs
        """
        return self.model.objects.filter(pk=obj_id).first()

    def message_template(self, message, obj):
        return {
            'to': obj.email,
            'subject': 'Message about {}'.format(str(obj)), # TODO? should we make it a setting?
            'message_text': message, # TODO? wrap in minimal template?
            'from_line': settings.FROM_EMAIL,
        }

    def send_messages(self, message, objects, actually_send=True, visibility=None):
        """
        1. create EmailMessage objects using template_func as an adapter/transformer to objects
        2. save message to object (in reviewlog or contactmessage thingie
        3. send the messages
        It will not check access control
        """
        messages = []
        for obj in objects:
            print(obj.id, obj)
            message_dict = self.message_template(message, obj)
            messages.append(create_message(**message_dict))
        if actually_send:
            connection = get_mail_connection()
            connection.send_messages(messages)
        else:
            print(messages) # TODO remove debug
        # save messages into reviewlog or similar
        if message and getattr(self, 'user'):
            msg_count = len(objects)
            for obj in objects:
                org = self.obj2org(obj)
                subject_id = self.obj2subjectid(obj)
                if visibility is None:
                    visibility = ReviewGroup.user_visibility(org.slug, self.user)
                review_log = ReviewLog.objects.create(content_type=ContentType.objects.get_for_model(obj._meta.model),
                                                      object_id=obj.id,
                                                      subject=subject_id,
                                                      organization_id=org.id,
                                                      reviewer=self.user,
                                                      log_type='message' if msg_count == 1 else 'bulk_msg',
                                                      visibility_level=int(visibility),
                                                      message=message)
        return messages

    def obj2org(self, obj):
        """How to get the organization from an object.  Override for a different way"""
        return obj.organization

    def obj2subjectid(self, obj):
        return None

    def send_message_widget(self, obj):
        try:
            api_link = reverse('admin:'+self.send_message_path(), args=[self.obj2org(obj).slug, obj.id])
            return mark_safe(
                render_to_string(
                    'reviewer/message_send_widget.html',
                    {'obj_id':obj.pk,
                     'widget_id': random.randint(1,10000),
                     'placeholder': self.send_a_message_placeholder,
                     'link': api_link}))
        except NoReverseMatch:
            return ''
    send_message_widget.short_description = 'Send a message'
    send_message_widget.allow_tags = True

    @staticmethod
    def bulk_message_send(modeladmin, request, queryset):
        """
        Message sending action for a ModelAdmin that will send messages to everyone
        chosen in a queryset
        """
        modeladmin.user = request.user
        title = "Send a message to many at once"
        objects_name = "tags"
        opts = modeladmin.model._meta
        action_checkbox_name="_selected_action"
        app_label = opts.app_label
        perms_needed = False # TODO: set permissions
        count = queryset.count()
        max_send = getattr(settings, "MESSAGE_SEND_MAX", 200)
        if not perms_needed count and count <= max_send:
            message = request.POST.get('message','')
            if message and request.POST.get('post'):
                modeladmin.send_messages(message, list(queryset),
                                         visibility=request.POST.get('visibility'))
                # Return None to display the change list page again.
                return None
        else:
            title = "Cannot send messages"

        context = dict(
            modeladmin.admin_site.each_context(request),
            title=title,
            visibility_options=ReviewGroup.user_visibility_options(
            objects_name=objects_name,
            queryset=queryset,
            count=count,
            max_send=max_send,
            perms_lacking=perms_needed,
            opts=opts,
            action_checkbox_name=action_checkbox_name,
            media=modeladmin.media
        )

        request.current_app = modeladmin.admin_site.name

        # Display the confirmation page
        return TemplateResponse(request, "reviewer/admin/bulk_message_send.html", context)

    
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
