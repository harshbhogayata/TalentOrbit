import os

from django.core.management.base import BaseCommand

from core.models import User


class Command(BaseCommand):
    help = 'Creates a superuser automatically when all bootstrap env vars are present'

    def handle(self, *args, **options):
        username = os.environ.get('SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('SUPERUSER_PASSWORD', '')

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    'Skipping superuser creation. Set SUPERUSER_USERNAME, SUPERUSER_EMAIL, and SUPERUSER_PASSWORD to enable bootstrap admin creation.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} already exists.'))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role='admin',
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Successfully created new superuser: {username}'))
