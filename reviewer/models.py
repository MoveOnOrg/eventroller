from __future__ import unicode_literals

from collections import OrderedDict
import datetime

from django.db import models
from django.conf import settings

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django_redis import get_redis_connection

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
    visibility_level = models.IntegerField(
        default=0,
        help_text=("Think of it like an access hierarchy. "
                   "0 is generally the lowest level. "
                   "Anything higher is probably staff/etc. "
                   "It affects what Reviews and Notes will be visible"))

    class Meta:
        unique_together = ('organization', 'group')

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
    def user_org_visibility(cls, organization_slug, user):
        org_groups = cls.org_groups(organization_slug)
        group_ids = set(user.groups.values_list('id', flat=True))
        visibility = None
        for org_grp in org_groups:
            if org_grp.group_id in group_ids:
                visibility = max(visibility, org_grp.visibility_level)
        return visibility

    @classmethod
    def user_review_groups(cls, user):
        return ReviewGroup.objects.filter(group__user=user)

    def __str__(self):
        return '{} for {}'.format(self.group, self.organization)

class Review(models.Model):
    content_type = models.ForeignKey(ContentType,
                                     editable=False,
                                     blank=True)
    object_id = models.IntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    obsoleted_at = models.DateTimeField(null=True, blank=True)

    organization = models.ForeignKey(Organization)
    reviewer = models.ForeignKey(User)
    key = models.CharField(max_length=128,
                           help_text=("the data key for what is being reviewed"
                                      " -- this allows multiple keys per-object"),
                           default="review")
    decision = models.CharField(max_length=128)
    visibility_level = models.IntegerField()

    @classmethod
    def bulk_add_tag(cls, content_queryset, organization, reviewer, key, decision):
        """
        Adds one tag at a time to selected object instances
        TODO: this may require more work when supporting multi-select
        """
        content_type = ContentType.objects.get_for_model(content_queryset.model)
        result = Review.objects.bulk_create([
            Review(organization=organization,
                   reviewer=reviewer,
                   key=key,
                   decision=decision,
                   object_id=obj_id,
                   content_type=content_type)
            for obj_id in content_queryset.values_list('id', flat=True)
        ])
        cls.bulk_clear_review_cache(content_queryset, organization)
        return result

    @classmethod
    def bulk_delete_tag(cls, content_queryset, organization, reviewer, key):
        """
        Deletes one tag at a time from selected object instances
        TODO: this may require more work when supporting multi-select
        """
        content_type = ContentType.objects.get_for_model(content_queryset.model)
        obj_ids = [x.id for x in content_queryset]
        result = Review.objects.filter(
            organization=organization,
            reviewer=reviewer,
            key=key,
            content_type=content_type,
            object_id__in=obj_ids
        ).update(obsoleted_at=datetime.datetime.now())
        cls.bulk_clear_review_cache(obj_ids, content_type.id, organization)
        return result

    @classmethod
    def bulk_clear_review_cache(cls, obj_ids, content_type_id, organization):
        """
        Clears cached reviews so we can update the display accurately
        after bulk delete/add
        """
        REDIS_CACHE_KEY = getattr(settings, 'REVIEWER_CACHE_KEY', 'default')
        redis = get_redis_connection(REDIS_CACHE_KEY)
        reviewskey = '{}_reviews'.format(organization.slug)
        obj_keys = ['{}_{}'.format(content_type_id, x) for x in obj_ids]
        if obj_keys:
            return redis.hdel(reviewskey, *obj_keys)
        return None

    @classmethod
    def reviews_by_object(cls, queryset=None, max=0, **filterargs):
        if not queryset:
            queryset = cls.objects
        if filterargs:
            queryset = queryset.filter(obsoleted_at=None).filter(**filterargs)
        query = queryset.order_by('-id')
        # can't use distinct() because sqlite doesn't support it
        # and postgres won't do it with an order_by
        # so we fake it:
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
                if max and len(db_res) > max:
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

    # subject is a secondary object reference,
    # like the host id when the object is an event
    subject = models.IntegerField(null=True, blank=True)

    organization = models.ForeignKey(Organization)
    reviewer = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()

    visibility_level = models.IntegerField()
