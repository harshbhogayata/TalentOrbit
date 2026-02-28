"""
Management command to reset is_subscribed for expired users.
Run via cron: python manage.py expire_subscriptions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import User


class Command(BaseCommand):
    help = 'Reset is_subscribed=False for users whose subscription has expired.'

    def handle(self, *args, **options):
        expired = User.objects.filter(
            is_subscribed=True,
            subscription_expiry__lt=timezone.now(),
        )
        count = expired.update(is_subscribed=False)
        self.stdout.write(self.style.SUCCESS(f'Reset {count} expired subscription(s).'))
