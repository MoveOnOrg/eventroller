from __future__ import unicode_literals

from collections import OrderedDict

from django.db import models

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from event_store.models import Organization


_ORGANIZATIONS = {}  # by slug

class ReviewGroup(models.Model):
    """
    many-to-many link of what groups can review for what organizations
    (TODO) Eventually, we may want a workflow that allows someone
    from one organization to vet events from another for the purposes
    of copying them over.  In that case, the org would allow sharing (see event_exim app)
    and wouldn't be added to the other org here, but a user might also be a member
    of more than one org, and both orgs might be ok with 'sharing' the vetting
    for the same event (assuming they have the same criteria).
    """
    organization = models.ForeignKey(Organization, db_index=True)
    group = models.ForeignKey(Group, db_index=True)


    @classmethod
    def org_groups(cls, organization_slug):
        """
        memo-ize orgs--it'll be a long time before we're too big for memory
        """
        if organization_slug not in _ORGANIZATIONS:
            _ORGANIZATIONS[organization_slug] = list(ReviewGroup.objects.filter(
                organization__slug=organization_slug))
        return _ORGANIZATIONS.get(organization_slug)

    @classmethod
    def user_review_groups(cls, user):
        return ReviewGroup.objects.filter(group__user=user)

class Review(models.Model):
    content_type = models.ForeignKey(ContentType,
                                     editable=False,
                                     blank=True)
    object_id = models.IntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    organization = models.ForeignKey(Organization)
    reviewer = models.ForeignKey(User)
    key = models.CharField(max_length=128,
                           help_text=("the data key for what is being reviewed"
                                      " -- this allows multiple keys per-object"),
                           default="review")
    decision = models.CharField(max_length=128)

    @classmethod
    def reviews_by_object(cls, queryset=None, max=0, **filterargs):
        if not queryset:
            queryset = cls.objects
        if filterargs:
            queryset = queryset.filter(**filterargs)
        query = queryset.order_by('-id')
        try:
            distinct = query.distinct('content_type', 'object_id', 'key')
            if max:
                distinct = distinct[:max]
            db_res = list(distinct)
        except NotImplementedError:
            # sqlite doesn't support 'DISTINCT ON' so we'll fake it
            db_res = []
            if max:
                query = query[:max*2] # double because could have dupes
            db_pre = list(query)
            already = set()
            for r in db_pre:
                key = (r.content_type_id, r.object_id, r.key)
                if key not in already:
                    db_res.append(r)
                    already.add(key)
                    if len(db_res) > max:
                        break
        if db_res:
            revs = OrderedDict()
            for rev in db_res:
                revs.setdefault(
                    (rev.content_type_id, rev.object_id),
                    {'type': rev.content_type_id,
                     'pk': rev.object_id}).update({rev.key: rev.decision})
            return revs

class ReviewLog(models.Model):
    content_type = models.ForeignKey(ContentType,
                                     editable=False,
                                     blank=True)
    object_id = models.IntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    organization = models.ForeignKey(Organization)
    reviewer = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
