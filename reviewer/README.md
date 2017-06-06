This is a generic reviewing module which comes with some (hacky) javascript to load
into an admin view.

In your admin view, you want to:

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

## Backend

The api leverages a redis store to queue changes and attention from the frontend.
