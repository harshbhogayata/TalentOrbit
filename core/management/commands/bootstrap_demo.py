import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from core.models import CompanyProfile, Job, JobCategory, Skill, User


PRIMARY_DEMO_INBOX = 'harshmbhogayata@gmail.com'
SECONDARY_DEMO_INBOX = 'harshmbhogayata5623@gmail.com'


def _gmail_alias(base_email, label):
    local, domain = base_email.split('@', 1)
    return f'{local}+{slugify(label)}@{domain}'


def _is_truthy(value):
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


class Command(BaseCommand):
    help = 'Bootstraps demo admin, company, user, and job records when explicitly enabled'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Run even if BOOTSTRAP_DEMO_DATA is not enabled in the environment.',
        )

    def handle(self, *args, **options):
        if not options['force'] and not _is_truthy(os.environ.get('BOOTSTRAP_DEMO_DATA', '')):
            self.stdout.write(
                self.style.WARNING(
                    'Skipping demo bootstrap. Set BOOTSTRAP_DEMO_DATA=true to seed deployed demo records.'
                )
            )
            return

        self.stdout.write('Bootstrapping demo records...')

        skills = self._ensure_skills()
        categories = self._ensure_categories()
        companies = self._ensure_companies()
        self._ensure_users(skills)
        self._ensure_admin()
        self._ensure_jobs(companies, categories)

        self.stdout.write(self.style.SUCCESS('Demo bootstrap complete.'))
        self.stdout.write('  Admin login: admin / demo1234')
        self.stdout.write('  Company login: techcorp / demo1234')
        self.stdout.write('  User login: john_doe / demo1234')

    def _ensure_skills(self):
        skill_names = [
            'Python',
            'JavaScript',
            'React',
            'Django',
            'PostgreSQL',
            'Figma',
            'UI/UX Design',
            'Machine Learning',
        ]
        skill_map = {}
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name},
            )
            skill_map[name] = skill
        return skill_map

    def _ensure_categories(self):
        categories_data = [
            ('Software Development', 'bi-code-slash'),
            ('Data Science & AI', 'bi-graph-up-arrow'),
            ('Design & Creative', 'bi-palette'),
            ('DevOps & Cloud', 'bi-cloud-arrow-up'),
        ]
        category_map = {}
        for name, icon in categories_data:
            category, _ = JobCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name, 'icon': icon, 'is_active': True},
            )
            category.name = name
            category.icon = icon
            category.is_active = True
            category.save(update_fields=['name', 'icon', 'is_active'])
            category_map[name] = category
        return category_map

    def _ensure_companies(self):
        companies_data = [
            {
                'username': 'techcorp',
                'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'techcorp'),
                'company_name': 'TechCorp Solutions',
                'industry': 'Technology',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'description': 'Cloud-native enterprise software and platform engineering.',
                'employee_count': '500-1000',
                'established_year': 2015,
            },
            {
                'username': 'designhub',
                'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'designhub'),
                'company_name': 'DesignHub Studio',
                'industry': 'Design',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'description': 'Product design studio building interfaces and brand systems.',
                'employee_count': '50-200',
                'established_year': 2018,
            },
            {
                'username': 'datawave',
                'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'datawave'),
                'company_name': 'DataWave AI',
                'industry': 'Artificial Intelligence',
                'city': 'Hyderabad',
                'state': 'Telangana',
                'description': 'Applied AI company shipping production ML systems.',
                'employee_count': '200-500',
                'established_year': 2019,
            },
        ]

        company_map = {}
        for data in companies_data:
            user, _ = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'role': 'company',
                    'email_verified': True,
                    'first_name': data['company_name'].split()[0],
                },
            )
            user.email = data['email']
            user.role = 'company'
            user.email_verified = True
            user.first_name = data['company_name'].split()[0]
            user.set_password('demo1234')
            user.save()

            profile, _ = CompanyProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': data['company_name'],
                    'industry': data['industry'],
                    'city': data['city'],
                    'state': data['state'],
                    'country': 'India',
                    'description': data['description'],
                    'employee_count': data['employee_count'],
                    'established_year': data['established_year'],
                    'status': 'approved',
                },
            )
            profile.company_name = data['company_name']
            profile.industry = data['industry']
            profile.city = data['city']
            profile.state = data['state']
            profile.country = 'India'
            profile.description = data['description']
            profile.employee_count = data['employee_count']
            profile.established_year = data['established_year']
            profile.status = 'approved'
            profile.save()
            company_map[data['company_name']] = profile
        return company_map

    def _ensure_users(self, skills):
        demo_users = [
            {
                'username': 'john_doe',
                'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'john-doe'),
                'first_name': 'John',
                'last_name': 'Doe',
                'skills': ['Python', 'React', 'Django'],
            },
            {
                'username': 'priya_sharma',
                'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'priya-sharma'),
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'skills': ['Figma', 'UI/UX Design'],
            },
            {
                'username': 'alex_kumar',
                'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'alex-kumar'),
                'first_name': 'Alex',
                'last_name': 'Kumar',
                'skills': ['Python', 'Machine Learning', 'PostgreSQL'],
            },
        ]

        for data in demo_users:
            user, _ = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'role': 'user',
                    'email_verified': True,
                    'bio': 'Demo candidate account for the hosted site.',
                },
            )
            user.email = data['email']
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.role = 'user'
            user.email_verified = True
            user.bio = 'Demo candidate account for the hosted site.'
            user.set_password('demo1234')
            user.save()
            user.skills.set([skills[name] for name in data['skills']])

    def _ensure_admin(self):
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'admin'),
                'role': 'admin',
                'email_verified': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.email = _gmail_alias(PRIMARY_DEMO_INBOX, 'admin')
        admin.role = 'admin'
        admin.email_verified = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('demo1234')
        admin.save()

    def _ensure_jobs(self, companies, categories):
        deadline = timezone.localdate() + timedelta(days=30)
        jobs_data = [
            {
                'company': 'TechCorp Solutions',
                'title': 'Senior Python Developer',
                'category': 'Software Development',
                'job_type': 'full_time',
                'experience': '3-5',
                'salary_min': Decimal('1200000'),
                'salary_max': Decimal('2000000'),
                'location': 'Bangalore, India',
                'description': 'Build backend services and ship scalable platform features.',
                'requirements': 'Strong Python, Django, PostgreSQL, and API design experience.',
            },
            {
                'company': 'DesignHub Studio',
                'title': 'UI/UX Designer',
                'category': 'Design & Creative',
                'job_type': 'full_time',
                'experience': '1-2',
                'salary_min': Decimal('600000'),
                'salary_max': Decimal('1000000'),
                'location': 'Mumbai, India',
                'description': 'Design polished product flows, prototypes, and visual systems.',
                'requirements': 'Strong Figma skills and a solid product design portfolio.',
            },
            {
                'company': 'DataWave AI',
                'title': 'Machine Learning Engineer',
                'category': 'Data Science & AI',
                'job_type': 'full_time',
                'experience': '3-5',
                'salary_min': Decimal('1500000'),
                'salary_max': Decimal('2500000'),
                'location': 'Hyderabad, India',
                'description': 'Train, evaluate, and deploy production machine learning pipelines.',
                'requirements': 'Python, model deployment, experimentation, and data tooling.',
            },
            {
                'company': 'TechCorp Solutions',
                'title': 'DevOps Engineer',
                'category': 'DevOps & Cloud',
                'job_type': 'full_time',
                'experience': '3-5',
                'salary_min': Decimal('1300000'),
                'salary_max': Decimal('2200000'),
                'location': 'Remote',
                'description': 'Own CI/CD, container infrastructure, and runtime reliability.',
                'requirements': 'Docker, cloud operations, Linux, and deployment automation.',
            },
        ]

        for data in jobs_data:
            job, _ = Job.objects.get_or_create(
                company=companies[data['company']],
                title=data['title'],
                defaults={
                    'category': categories[data['category']],
                    'description': data['description'],
                    'requirements': data['requirements'],
                    'job_type': data['job_type'],
                    'experience': data['experience'],
                    'salary_min': data['salary_min'],
                    'salary_max': data['salary_max'],
                    'location': data['location'],
                    'is_active': True,
                    'deadline': deadline,
                },
            )
            job.category = categories[data['category']]
            job.description = data['description']
            job.requirements = data['requirements']
            job.job_type = data['job_type']
            job.experience = data['experience']
            job.salary_min = data['salary_min']
            job.salary_max = data['salary_max']
            job.location = data['location']
            job.is_active = True
            job.deadline = deadline
            job.save()
