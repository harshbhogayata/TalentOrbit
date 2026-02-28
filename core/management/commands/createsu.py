from django.core.management.base import BaseCommand
from core.models import User
import os

class Command(BaseCommand):
    help = 'Creates a superuser automatically'

    def handle(self, *args, **options):
        username = os.environ.get('SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('SUPERUSER_PASSWORD', 'admin123!')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                user_type='admin',
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created new superuser: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} already exists.'))
