from django.core.management.base import BaseCommand
from core.models import User, CompanyProfile, JobCategory, Job
from django.utils import timezone
from datetime import timedelta
import random

PRIMARY_DEMO_INBOX = 'harshmbhogayata@gmail.com'
SECONDARY_DEMO_INBOX = 'harshmbhogayata5623@gmail.com'


class Command(BaseCommand):
    help = 'Populates the database with dummy data and test accounts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting database populate process...')

        # 1. Create Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={},
        )
        admin_user.email = f"harshmbhogayata+admin@{PRIMARY_DEMO_INBOX.split('@', 1)[1]}"
        admin_user.role = 'admin'
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.email_verified = True
        admin_user.set_password('admin123!')
        admin_user.save()
        if created:
            self.stdout.write(self.style.SUCCESS('Admin user created: admin / admin123!'))

        # 2. Create Company User
        company_user, created = User.objects.get_or_create(
            username='techcorp',
            defaults={}
        )
        company_user.email = f"harshmbhogayata5623+techcorp@{SECONDARY_DEMO_INBOX.split('@', 1)[1]}"
        company_user.role = 'company'
        company_user.email_verified = True
        company_user.set_password('company123!')
        company_user.save()
        if created:
            
            # Create Company Profile
            company_profile, _ = CompanyProfile.objects.get_or_create(
                user=company_user,
                defaults={
                    'company_name': 'TechCorp Solutions',
                    'employer_type': 'tech',
                    'industry': 'Software Development',
                    'description': 'A leading technology solutions provider.',
                    'status': 'approved'
                }
            )
            self.stdout.write(self.style.SUCCESS('Company user created: techcorp / company123!'))
        else:
             company_profile = company_user.company_profile

        # 3. Create Regular User
        regular_user, created = User.objects.get_or_create(
            username='johndoe',
            defaults={}
        )
        regular_user.email = f"harshmbhogayata+johndoe@{PRIMARY_DEMO_INBOX.split('@', 1)[1]}"
        regular_user.role = 'user'
        regular_user.first_name = 'John'
        regular_user.last_name = 'Doe'
        regular_user.email_verified = True
        regular_user.set_password('user123!')
        regular_user.save()
        if created:
            self.stdout.write(self.style.SUCCESS('Regular user created: johndoe / user123!'))

        # 4. Create Job Categories
        categories = ['Frontend Development', 'Backend Development', 'DevOps', 'UI/UX Design']
        cat_objs = []
        for cat_name in categories:
            cat, _ = JobCategory.objects.get_or_create(name=cat_name, defaults={'is_active': True})
            cat_objs.append(cat)
        
        # 5. Create Dummy Jobs
        if not Job.objects.filter(company=company_profile).exists():
            job_titles = ['Senior React Developer', 'Python Backend Engineer', 'Cloud Infrastructure Architect']
            for title in job_titles:
                Job.objects.create(
                    company=company_profile,
                    category=random.choice(cat_objs),
                    title=title,
                    job_type=random.choice(['ft', 'ct']),
                    experience_level=random.choice(['mid', 'sen']),
                    location='Remote',
                    salary_min=80000,
                    salary_max=150000,
                    description=f'We are looking for an experienced {title}.',
                    requirements='3+ years of experience.',
                    is_active=True,
                    deadline=timezone.now().date() + timedelta(days=30)
                )
            self.stdout.write(self.style.SUCCESS(f'Generated {len(job_titles)} dummy jobs for TechCorp.'))

        self.stdout.write(self.style.SUCCESS('Database successfully populated!'))
