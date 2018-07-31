import django.dispatch

review_log_saved = django.dispatch.Signal(
    providing_args=['coreuser', 'tags', 'note'])
