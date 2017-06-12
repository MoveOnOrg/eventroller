If you want to allow the review of your records in admin,
this is an easy, generic add-on that will work for speed/scale/access-control of reviewers.

To do this, in your admin view:

```python
from reviewer.filters import ReviewerOrganizationFilter, review_widget
```

and then inside your admin hook both of those up like so:

```python
FooAdmin(admin.ModelAdmin):

   list_filter = (ReviewerOrganizationFilter,
                  ...)
   list_display = [..., review_widget]
```

This was built to review Events (i.e. `event_store.models.Events`) and is tied
to `event_store.models.Organization`.

Adding the ReviewerOrganizationFilter will, by default, try to filter on a field
called `organization`.  If the field is something else, subclass ReviewerOrganizationFilter
and change the class' `fieldname` value.

## Backend

The api leverages a redis store to queue changes and attention from the frontend.

