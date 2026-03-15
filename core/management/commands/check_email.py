from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.utils import get_default_from_email, send_email_result


class Command(BaseCommand):
    help = 'Verify email delivery configuration by sending a test email.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipient',
            help='Email address to receive the test message. Defaults to EMAIL_HOST_USER or DEFAULT_FROM_EMAIL.',
        )
        parser.add_argument(
            '--subject',
            default='TalentOrbit email delivery check',
            help='Subject line for the test message.',
        )

    def handle(self, *args, **options):
        recipient = (options.get('recipient') or getattr(settings, 'EMAIL_HOST_USER', '') or get_default_from_email()).strip()
        if not recipient:
            raise CommandError('Provide --recipient or configure EMAIL_HOST_USER/DEFAULT_FROM_EMAIL.')

        self.stdout.write(f'Backend: {getattr(settings, "EMAIL_BACKEND", "") or "(unset)"}')
        self.stdout.write(f'Host: {getattr(settings, "EMAIL_HOST", "") or "(unset)"}:{getattr(settings, "EMAIL_PORT", "") or "(unset)"}')
        self.stdout.write(f'TLS: {bool(getattr(settings, "EMAIL_USE_TLS", False))}  SSL: {bool(getattr(settings, "EMAIL_USE_SSL", False))}')
        fallback_port = int(getattr(settings, 'EMAIL_FALLBACK_PORT', 0) or 0)
        if fallback_port > 0:
            self.stdout.write(
                f'Fallback transport: port={fallback_port} ssl={bool(getattr(settings, "EMAIL_FALLBACK_USE_SSL", False))} tls={bool(getattr(settings, "EMAIL_FALLBACK_USE_TLS", False))}'
            )

        result = send_email_result(
            options['subject'],
            'This is a TalentOrbit email delivery health check.',
            [recipient],
            require_external_delivery=True,
        )
        if not result:
            raise CommandError(f'Email delivery check failed ({result.error_code}).')

        self.stdout.write(self.style.SUCCESS(f'Email delivery check passed. Sent test email to {recipient}.'))
