from .models import Notification


def notifications(request):
    """
    Inject unread notification count into every template context.
    Caches the count on the request object to avoid duplicate DB hits
    if the processor is called more than once per request cycle.
    """
    if not request.user.is_authenticated:
        return {'unread_count': 0}

    # Per-request cache: avoids a second query if something else
    # in the same request already computed this.
    if not hasattr(request, '_cached_unread_count'):
        request._cached_unread_count = (
            Notification.objects
            .filter(recipient=request.user, is_read=False)
            .count()
        )
    return {'unread_count': request._cached_unread_count}
