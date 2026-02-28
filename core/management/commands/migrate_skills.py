from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Legacy migration tool — skills are now a ManyToManyField, no migration needed'

    def handle(self, *args, **kwargs):
        self.stdout.write('Skills are already stored as a ManyToManyField.')
        self.stdout.write('This command is kept for backwards compatibility only.')
        self.stdout.write(self.style.SUCCESS('No action needed.'))
