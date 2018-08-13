from django.contrib import admin

from reviewer.models import ReviewGroup, ReviewLog

@admin.register(ReviewGroup)
class ReviewGroupAdmin(admin.ModelAdmin):
    list_display = ['organization', 'group', 'visibility_level']

@admin.register(ReviewLog)
class ReviewGroupAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'object_id', 'subject',
                    'reviewer',
                    'created_at',
                    'visibility_level',
                    'log_type', 'message']
    search_fields = ['subject', 'object_id', 'message']
