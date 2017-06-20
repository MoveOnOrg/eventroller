from django.contrib import admin

from reviewer.models import ReviewGroup

@admin.register(ReviewGroup)
class ReviewGroupAdmin(admin.ModelAdmin):
    #list_display = ['organization', 'group']
    pass
