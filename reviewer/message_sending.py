import datetime
import json
import random

from django.core.mail import get_connection as get_mail_connection
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
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

    def send_message_path(self):
        return '{app_label}_{model_name}_send_message'.format(
            app_label=self.model._meta.app_label,
            model_name=self.model._meta.model_name)

    def get_urls(self):
        urls = admin.ModelAdmin.get_urls(self)
        my_urls = [
            # must NOT end in a '/' or it will get matched with an admin
            # blanket-match. See django.contrib.admin.options.ModelAdmin.get_urls
            url('send_message/(?P<organization>[-.\w]+)/(?P<obj_id>[-.\w]+)',
                self.admin_site.admin_view(self.send_message),
                name=self.send_message_path())
        ]
        return urls + my_urls

    def get_actions(self, request):
        actions = admin.ModelAdmin.get_actions(self, request) or {}
        if request.user.has_perm('reviewer.bulk_message_send'):
            actions.update({'bulk_message_send': (
                self.bulk_message_send,
                'bulk_message_send',
                'Send a message to many people')})
        if request.user.has_perm('reviewer.bulk_note_add'):
            actions.update({'bulk_note_add': (
                self.bulk_note_add,
                'bulk_note_add',
                'Bulk add a note')})
        return actions

    def send_message(self, request, organization, obj_id):
        result = 'failed to send'
        if not ReviewGroup.user_allowed(request.user, organization)\
           or not request.user.has_perm('reviewer.message_sending'):
            result = 'permission denied'
        elif request.method == 'POST' and self.message_send_ready(organization, request):
            obj = self.message_obj_lookup(obj_id, organization, request)
            if obj:
                self.deploy_messages(request.POST.get('message',''), [obj],
                                     log_type='message',
                                     visibility=request.POST.get('visibility'),
                                     user=request.user)
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

    def message_template(self, message, obj, user=None):
        return {
            'to': obj.email,
            'subject': 'Message about {}'.format(str(obj)), # TODO? should we make it a setting?
            'message_text': message, # TODO? wrap in minimal template?
            'from_line': settings.FROM_EMAIL,
        }

    def deploy_messages(self, message, objects, log_type='message', visibility=None, user=None, actually_send=True):
        """
        1. create EmailMessage objects using template_func as an adapter/transformer to objects
        2. save message to object (in reviewlog or contactmessage thingie
        3. send the messages
        It will not check access control
        """
        bulktypes = {'message': 'bulkmsg', 'note': 'bulknote'}
        messages = []
        review_logs = []
        if log_type in ('message', 'bulkmsg'):
            for obj in objects:
                message_dict = self.message_template(message, obj, user)
                messages.append(create_message(**message_dict))
            if actually_send:
                connection = get_mail_connection()
                if hasattr(connection, 'open'):
                    connection.open()
                connection.send_messages(messages)
        # save messages into reviewlog or similar
        if message and user:
            msg_count = len(objects)
            for obj in objects:
                org = self.obj2org(obj)
                subject_id = self.obj2subjectid(obj)
                if visibility is None:
                    visibility = ReviewGroup.user_visibility(org.slug, user)
                review_logs.append(ReviewLog(content_type=ContentType.objects.get_for_model(obj._meta.model),
                                             object_id=obj.id,
                                             subject=subject_id,
                                             organization_id=org.id,
                                             reviewer=user,
                                             log_type=(log_type if msg_count == 1
                                                       else bulktypes.get(log_type, log_type)),
                                             visibility_level=int(visibility),
                                             message=message))
            if review_logs:
                ReviewLog.objects.bulk_create(review_logs)
        return (messages, review_logs)

    def obj2org(self, obj):
        """How to get the organization from an object.  Override for a different way"""
        return obj.organization

    def obj2subjectid(self, obj):
        return None

    def obj_person_noun(self):
        return 'host'

    def send_message_widget(self, obj):
        try:
            org = self.obj2org(obj)
            api_link = reverse('admin:'+self.send_message_path(), args=[org.slug, obj.id])
            return mark_safe(
                render_to_string(
                    'reviewer/message_send_widget.html',
                    {'obj_id':obj.pk,
                     'widget_id': random.randint(1,10000),
                     'placeholder': self.send_a_message_placeholder,
                     'nounperson': self.obj_person_noun(),
                     'link': api_link}))
        except NoReverseMatch:
            return ''
    send_message_widget.short_description = 'Send a message'
    send_message_widget.allow_tags = True

    @staticmethod
    def bulk_note_add(modeladmin, request, queryset):
        return MessageSendingAdminMixin.bulk_content_action(
            modeladmin, request, queryset,
            log_type='note',
            action='bulk_note_add',
            verb='add note')

    @staticmethod
    def bulk_message_send(modeladmin, request, queryset):
        return MessageSendingAdminMixin.bulk_content_action(
            modeladmin, request, queryset,
            log_type='message',
            action='bulk_message_send',
            verb='send a message')

    @staticmethod
    def bulk_content_action(modeladmin, request, queryset, log_type, action, verb):
        """
        Message sending action for a ModelAdmin that will send messages to everyone
        chosen in a queryset
        """
        title = "{} to many at once".format(verb)
        objects_name = "tags"
        opts = modeladmin.model._meta
        action_checkbox_name="_selected_action"
        app_label = opts.app_label
        no_continue_message = ''
        perms_needed = not request.user.has_perm('reviewer.{}'.format(action))
        if perms_needed:
            no_continue_message = 'Contact a site administrator about getting permission to {}.'.format(action)
        count = queryset.count()
        max_apply = getattr(settings, "BULK_NOTEMESSAGE_MAX", 200)

        organization_slug = request.POST.get('organization')
        if not organization_slug:
            orgslugs = (ReviewGroup
                        .user_review_groups(request.user)
                        .values_list('organization__slug', flat=True)
                        .distinct())
            if len(orgslugs) == 1:
                organization_slug = orgslugs[0]

        if log_type in ('message', 'bulkmsg'):
            howmany = ReviewLog.objects.filter(reviewer=request.user,
                                               log_type__in=('message', 'bulkmsg'))
            curtime = datetime.datetime.now()
            weekcount = howmany.filter(created_at__gte=curtime-datetime.timedelta(days=7)).count()
            daycount = howmany.filter(created_at__gte=curtime-datetime.timedelta(days=1)).count()
            max_daycount = getattr(settings, 'BULK_NOTEMESSAGE_DAY_MAX', 200)
            max_weekcount = getattr(settings, 'BULK_NOTEMESSAGE_WEEK_MAX', 200)
            if (daycount + count) > max_daycount:
                no_continue_message = 'This exceeds your daily contact count of {}.'.format(max_daycount)
            elif (weekcount + count) > max_weekcount:
                no_continue_message = 'This exceeds your weekly contact count of {}.'.format(max_weekcount)

        if not perms_needed and count and count <= max_apply:
            message = request.POST.get('message','')
            if message and request.POST.get('post'):
                visibility = request.POST.get('visibility')
                if visibility is None:
                    visibility = ReviewGroup.user_visibility(organization_slug, request.user)
                modeladmin.deploy_messages(message, list(queryset),
                                           log_type=log_type,
                                           visibility=visibility,
                                           user=request.user)
                # Return None to display the change list page again.
                return None
        else:
            title = "Cannot send messages"

        context = dict(
            modeladmin.admin_site.each_context(request),
            title=title,
            organization_slug=organization_slug,
            visibility_options=(
                ReviewGroup.user_visibility_options(organization_slug, request.user).items()
                if organization_slug else None),
            objects_name=objects_name,
            queryset=queryset,
            count=count,
            max_apply=max_apply,
            perms_lacking=perms_needed,
            no_continue_message=no_continue_message,
            opts=opts,
            action_checkbox_name=action_checkbox_name,
            media=modeladmin.media,
            verb=verb,
            action=action
        )

        request.current_app = modeladmin.admin_site.name

        # Display the confirmation page
        return TemplateResponse(request, "reviewer/admin/bulk_content_action.html", context)

    
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
