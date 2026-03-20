"""
Seed mock data into the database for development/demo purposes.
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
from decimal import Decimal

from core.models import (
    User, CompanyProfile, JobCategory, Job, Skill, Notification,
    JobApplication, SavedJob, Tender, TenderBid,
    Quiz, QuizQuestion, QuizAttempt, Subscription, NewsletterSubscription,
    SkillVideo,
)
import os
from django.conf import settings
from django.core.files.base import ContentFile

PRIMARY_DEMO_INBOX = 'harshmbhogayata@gmail.com'
SECONDARY_DEMO_INBOX = 'harshmbhogayata5623@gmail.com'


def _gmail_alias(base_email, label):
    local, domain = base_email.split('@', 1)
    return f'{local}+{slugify(label)}@{domain}'


class Command(BaseCommand):
    help = 'Seed the database with mock data for development'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # ── Skills ──────────────────────────────────────────
        skill_names = [
            'Python', 'JavaScript', 'React', 'Django', 'Node.js',
            'TypeScript', 'PostgreSQL', 'Docker', 'AWS', 'Git',
            'Java', 'C++', 'Go', 'Rust', 'Kubernetes',
            'GraphQL', 'REST API', 'MongoDB', 'Redis', 'Linux',
            'Figma', 'UI/UX Design', 'Machine Learning', 'Data Science',
            'DevOps', 'CI/CD', 'Agile', 'Scrum',
        ]
        skills = {}
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name}
            )
            skills[name] = skill
        self.stdout.write(f'  Created {len(skill_names)} skills')

        # ── Categories ──────────────────────────────────────
        categories_data = [
            ('Software Development', 'bi-code-slash'),
            ('Data Science & AI', 'bi-graph-up-arrow'),
            ('Design & Creative', 'bi-palette'),
            ('Marketing', 'bi-megaphone'),
            ('DevOps & Cloud', 'bi-cloud-arrow-up'),
            ('Product Management', 'bi-kanban'),
            ('Cybersecurity', 'bi-shield-lock'),
            ('Mobile Development', 'bi-phone'),
        ]
        cats = {}
        for name, icon in categories_data:
            cat, _ = JobCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name, 'icon': icon, 'is_active': True}
            )
            cats[name] = cat
        self.stdout.write(f'  Created {len(categories_data)} categories')

        # ── Companies ───────────────────────────────────────
        companies_data = [
            {
                'username': 'techcorp', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'techcorp'),
                'company_name': 'TechCorp Solutions', 'industry': 'Technology',
                'city': 'Bangalore', 'state': 'Karnataka',
                'description': 'Leading enterprise software company specializing in cloud-native solutions and digital transformation.',
                'employee_count': '500-1000', 'established_year': 2015,
            },
            {
                'username': 'designhub', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'designhub'),
                'company_name': 'DesignHub Studio', 'industry': 'Design',
                'city': 'Mumbai', 'state': 'Maharashtra',
                'description': 'Award-winning design agency creating beautiful digital experiences for global brands.',
                'employee_count': '50-200', 'established_year': 2018,
            },
            {
                'username': 'datawave', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'datawave'),
                'company_name': 'DataWave AI', 'industry': 'Artificial Intelligence',
                'city': 'Hyderabad', 'state': 'Telangana',
                'description': 'Pioneering AI research lab building next-generation machine learning platforms.',
                'employee_count': '200-500', 'established_year': 2019,
            },
            {
                'username': 'cloudnine', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'cloudnine'),
                'company_name': 'CloudNine Infra', 'industry': 'Cloud Computing',
                'city': 'Pune', 'state': 'Maharashtra',
                'description': 'Multi-cloud infrastructure provider offering scalable DevOps and managed services.',
                'employee_count': '100-500', 'established_year': 2017,
            },
            {
                'username': 'nexasoft', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'nexasoft'),
                'company_name': 'NexaSoft Technologies', 'industry': 'Fintech',
                'city': 'Chennai', 'state': 'Tamil Nadu',
                'description': 'Fintech innovator building secure payment systems and digital banking solutions.',
                'employee_count': '1000+', 'established_year': 2012,
            },
            {
                'username': 'greenleaf', 'email': _gmail_alias(SECONDARY_DEMO_INBOX, 'greenleaf'),
                'company_name': 'GreenLeaf Digital', 'industry': 'Digital Marketing',
                'city': 'Delhi', 'state': 'Delhi',
                'description': 'Full-service digital marketing agency helping startups scale with data-driven strategies.',
                'employee_count': '50-100', 'established_year': 2020,
            },
        ]

        company_profiles = {}
        for cd in companies_data:
            user, created = User.objects.get_or_create(
                username=cd['username'],
                defaults={
                    'email': cd['email'],
                    'role': 'company',
                    'email_verified': True,
                    'first_name': cd['company_name'].split()[0],
                }
            )
            user.email = cd['email']
            user.role = 'company'
            user.email_verified = True
            user.first_name = cd['company_name'].split()[0]
            user.set_password('demo1234')
            user.save()

            profile, _ = CompanyProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': cd['company_name'],
                    'industry': cd['industry'],
                    'city': cd['city'],
                    'state': cd['state'],
                    'country': 'India',
                    'description': cd['description'],
                    'employee_count': cd['employee_count'],
                    'established_year': cd['established_year'],
                    'status': 'approved',
                }
            )
            profile.company_name = cd['company_name']
            profile.industry = cd['industry']
            profile.city = cd['city']
            profile.state = cd['state']
            profile.country = 'India'
            profile.description = cd['description']
            profile.employee_count = cd['employee_count']
            profile.established_year = cd['established_year']
            profile.status = 'approved'
            profile.save()
            company_profiles[cd['company_name']] = profile
        self.stdout.write(f'  Created {len(companies_data)} companies')

        # ── Jobs ────────────────────────────────────────────
        now = timezone.now()
        jobs_data = [
            {
                'company': 'TechCorp Solutions', 'title': 'Senior Python Developer',
                'category': 'Software Development', 'job_type': 'full_time', 'experience': '3-5',
                'salary_min': 1200000, 'salary_max': 2000000, 'location': 'Bangalore, India',
                'description': 'We are looking for a Senior Python Developer to join our backend engineering team. You will design and build scalable microservices, mentor junior developers, and drive technical decisions for our cloud platform.',
                'requirements': 'Strong experience with Python, Django/FastAPI, PostgreSQL, Docker, and REST APIs. Familiarity with AWS services preferred.',
                'skills': ['Python', 'Django', 'PostgreSQL', 'Docker', 'AWS'],
                'days_ago': 2,
            },
            {
                'company': 'TechCorp Solutions', 'title': 'Full Stack Engineer',
                'category': 'Software Development', 'job_type': 'full_time', 'experience': '1-2',
                'salary_min': 800000, 'salary_max': 1400000, 'location': 'Bangalore, India',
                'description': 'Join our product team as a Full Stack Engineer. You will build features end-to-end using React and Django, collaborate closely with designers, and ship features that impact thousands of users.',
                'requirements': 'Proficiency in React, JavaScript/TypeScript, Python, and Django. Understanding of RESTful APIs and Git.',
                'skills': ['React', 'JavaScript', 'Python', 'Django', 'Git'],
                'days_ago': 5,
            },
            {
                'company': 'DesignHub Studio', 'title': 'UI/UX Designer',
                'category': 'Design & Creative', 'job_type': 'full_time', 'experience': '1-2',
                'salary_min': 600000, 'salary_max': 1000000, 'location': 'Mumbai, India',
                'description': 'We need a creative UI/UX Designer to craft intuitive user experiences for web and mobile applications. You will work with product managers and developers to turn ideas into pixel-perfect designs.',
                'requirements': 'Expert in Figma, strong portfolio, understanding of design systems and accessibility. Experience with user research is a plus.',
                'skills': ['Figma', 'UI/UX Design'],
                'days_ago': 1,
            },
            {
                'company': 'DataWave AI', 'title': 'Machine Learning Engineer',
                'category': 'Data Science & AI', 'job_type': 'full_time', 'experience': '3-5',
                'salary_min': 1500000, 'salary_max': 2500000, 'location': 'Hyderabad, India',
                'description': 'Build and deploy production ML models at scale. Work on NLP, computer vision, and recommendation systems. Collaborate with research scientists to bring cutting-edge algorithms to production.',
                'requirements': 'Strong in Python, PyTorch/TensorFlow, MLOps pipelines, and cloud deployment. MS/PhD in CS or related field preferred.',
                'skills': ['Python', 'Machine Learning', 'Data Science', 'Docker', 'AWS'],
                'days_ago': 3,
            },
            {
                'company': 'DataWave AI', 'title': 'Data Scientist',
                'category': 'Data Science & AI', 'job_type': 'full_time', 'experience': '1-2',
                'salary_min': 900000, 'salary_max': 1500000, 'location': 'Hyderabad, India',
                'description': 'Analyze large datasets to derive actionable insights. Build dashboards, run experiments, and develop predictive models to drive business decisions across the organization.',
                'requirements': 'Python, SQL, pandas, scikit-learn. Experience with A/B testing and statistical analysis.',
                'skills': ['Python', 'Data Science', 'PostgreSQL'],
                'days_ago': 7,
            },
            {
                'company': 'CloudNine Infra', 'title': 'DevOps Engineer',
                'category': 'DevOps & Cloud', 'job_type': 'full_time', 'experience': '3-5',
                'salary_min': 1300000, 'salary_max': 2200000, 'location': 'Pune, India',
                'description': 'Design and maintain CI/CD pipelines, manage Kubernetes clusters, and ensure 99.99% uptime for our cloud infrastructure. You will be the backbone of our engineering reliability.',
                'requirements': 'Deep knowledge of Kubernetes, Docker, Terraform, AWS/GCP. Experience with monitoring tools like Prometheus and Grafana.',
                'skills': ['Docker', 'Kubernetes', 'AWS', 'Linux', 'CI/CD', 'DevOps'],
                'days_ago': 4,
            },
            {
                'company': 'CloudNine Infra', 'title': 'Cloud Solutions Architect',
                'category': 'DevOps & Cloud', 'job_type': 'full_time', 'experience': '5-10',
                'salary_min': 2500000, 'salary_max': 4000000, 'location': 'Pune, India (Hybrid)',
                'description': 'Lead the architecture of multi-cloud solutions for enterprise clients. Define best practices, conduct architecture reviews, and mentor the engineering team on cloud-native patterns.',
                'requirements': 'AWS/Azure/GCP certified. 7+ years in cloud architecture. Strong communication skills for client-facing work.',
                'skills': ['AWS', 'Kubernetes', 'DevOps'],
                'days_ago': 6,
            },
            {
                'company': 'NexaSoft Technologies', 'title': 'Backend Developer (Java)',
                'category': 'Software Development', 'job_type': 'full_time', 'experience': '1-2',
                'salary_min': 700000, 'salary_max': 1200000, 'location': 'Chennai, India',
                'description': 'Develop high-performance backend services for our digital banking platform using Java and Spring Boot. Handle millions of transactions daily with zero downtime.',
                'requirements': 'Java, Spring Boot, MySQL/PostgreSQL, microservices architecture. Understanding of payment systems is a bonus.',
                'skills': ['Java', 'PostgreSQL', 'REST API', 'Docker', 'Git'],
                'days_ago': 3,
            },
            {
                'company': 'NexaSoft Technologies', 'title': 'Cybersecurity Analyst',
                'category': 'Cybersecurity', 'job_type': 'full_time', 'experience': '3-5',
                'salary_min': 1100000, 'salary_max': 1800000, 'location': 'Chennai, India',
                'description': 'Protect our fintech infrastructure from threats. Conduct penetration testing, monitor security events, and implement security controls across cloud and on-premise systems.',
                'requirements': 'CISSP/CEH certification preferred. Experience with SIEM tools, vulnerability scanning, and incident response.',
                'skills': ['Linux', 'Python'],
                'days_ago': 8,
            },
            {
                'company': 'GreenLeaf Digital', 'title': 'Digital Marketing Manager',
                'category': 'Marketing', 'job_type': 'full_time', 'experience': '3-5',
                'salary_min': 800000, 'salary_max': 1400000, 'location': 'Delhi, India',
                'description': 'Lead our marketing efforts across SEO, SEM, social media, and content marketing. Drive growth for our portfolio of 20+ startup clients through data-driven campaigns.',
                'requirements': 'Expert in Google Ads, Meta Ads, SEO tools, and analytics platforms. Strong copywriting and team leadership skills.',
                'skills': ['Agile'],
                'days_ago': 2,
            },
            {
                'company': 'DesignHub Studio', 'title': 'Frontend Developer (React)',
                'category': 'Software Development', 'job_type': 'contract', 'experience': '1-2',
                'salary_min': 500000, 'salary_max': 900000, 'location': 'Remote',
                'description': 'Build responsive and accessible web interfaces for our client projects. Collaborate with designers to implement pixel-perfect UIs using React and modern CSS.',
                'requirements': 'React, TypeScript, CSS/Tailwind, responsive design. Eye for detail and design sensibility.',
                'skills': ['React', 'TypeScript', 'JavaScript', 'Git'],
                'days_ago': 1,
            },
            {
                'company': 'GreenLeaf Digital', 'title': 'Content Writer Intern',
                'category': 'Marketing', 'job_type': 'internship', 'experience': 'fresher',
                'salary_min': 10000, 'salary_max': 20000, 'location': 'Delhi, India',
                'description': 'Write blog posts, social media captions, and email newsletters for our clients. Learn the ropes of content marketing from experienced professionals.',
                'requirements': 'Excellent written English. Curiosity about digital marketing. Portfolio of writing samples preferred.',
                'skills': [],
                'days_ago': 0,
            },
            {
                'company': 'TechCorp Solutions', 'title': 'Product Manager',
                'category': 'Product Management', 'job_type': 'full_time', 'experience': '5-10',
                'salary_min': 2000000, 'salary_max': 3500000, 'location': 'Bangalore, India',
                'description': 'Own the product roadmap for our enterprise SaaS platform. Drive product strategy, prioritize features based on customer feedback, and work cross-functionally with engineering and design.',
                'requirements': '5+ years in product management at a tech company. Strong analytical skills, SQL proficiency, and experience with agile methodologies.',
                'skills': ['Agile', 'Scrum'],
                'days_ago': 4,
            },
            {
                'company': 'DataWave AI', 'title': 'Mobile Developer (React Native)',
                'category': 'Mobile Development', 'job_type': 'remote', 'experience': '1-2',
                'salary_min': 800000, 'salary_max': 1300000, 'location': 'Remote',
                'description': 'Build cross-platform mobile apps for our AI-powered data tools. Work on real-time data visualization and offline-first architecture.',
                'requirements': 'React Native, JavaScript/TypeScript, REST APIs. Experience with mobile app deployment (App Store/Play Store).',
                'skills': ['React', 'JavaScript', 'TypeScript', 'REST API'],
                'days_ago': 5,
            },
        ]

        created_count = 0
        for jd in jobs_data:
            company = company_profiles[jd['company']]
            category = cats[jd['category']]
            created_at = now - timedelta(days=jd['days_ago'])

            if not Job.objects.filter(title=jd['title'], company=company).exists():
                job = Job.objects.create(
                    company=company,
                    title=jd['title'],
                    category=category,
                    job_type=jd['job_type'],
                    experience=jd['experience'],
                    salary_min=Decimal(str(jd['salary_min'])),
                    salary_max=Decimal(str(jd['salary_max'])),
                    location=jd['location'],
                    description=jd['description'],
                    requirements=jd['requirements'],
                    is_active=True,
                    deadline=now.date() + timedelta(days=30),
                )
                # Backdate created_at
                Job.objects.filter(pk=job.pk).update(created_at=created_at)
                # Add skills
                for skill_name in jd['skills']:
                    if skill_name in skills:
                        job.skills.add(skills[skill_name])
                created_count += 1

        self.stdout.write(f'  Created {created_count} jobs')

        # ── Demo Users ──────────────────────────────────────
        demo_users = [
            {'username': 'john_doe', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'john-doe'), 'first_name': 'John', 'last_name': 'Doe'},
            {'username': 'priya_sharma', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'priya-sharma'), 'first_name': 'Priya', 'last_name': 'Sharma'},
            {'username': 'alex_kumar', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'alex-kumar'), 'first_name': 'Alex', 'last_name': 'Kumar'},
        ]
        for ud in demo_users:
            user, created = User.objects.get_or_create(
                username=ud['username'],
                defaults={
                    'email': ud['email'],
                    'first_name': ud['first_name'],
                    'last_name': ud['last_name'],
                    'role': 'user',
                    'email_verified': True,
                    'bio': f"Passionate developer looking for exciting opportunities.",
                }
            )
            user.email = ud['email']
            user.first_name = ud['first_name']
            user.last_name = ud['last_name']
            user.role = 'user'
            user.email_verified = True
            user.bio = "Passionate developer looking for exciting opportunities."
            user.set_password('demo1234')
            user.save()
            if created:
                user.skills.add(skills['Python'], skills['JavaScript'], skills['React'])

        self.stdout.write(f'  Created {len(demo_users)} demo users')

        # ── Admin User ──────────────────────────────────────
        admin = User.objects.filter(username='admin').first()
        if not admin:
            admin = User.objects.create_superuser(
                username='admin',
                email=_gmail_alias(PRIMARY_DEMO_INBOX, 'admin'),
                password='demo1234',
                role='admin',
                email_verified=True
            )
            self.stdout.write('  Created Admin user: admin / demo1234')
        else:
            admin.email = _gmail_alias(PRIMARY_DEMO_INBOX, 'admin')
            admin.role = 'admin'
            admin.email_verified = True
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password('demo1234')
            admin.save()
            self.stdout.write('  Reset Admin user credentials: admin / demo1234')

        # ── Additional Candidates ───────────────────────────
        new_candidates = [
            {'username': 'rahul_verma', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'rahul-verma'), 'first_name': 'Rahul', 'last_name': 'Verma', 'skills': ['Python', 'Django', 'PostgreSQL']},
            {'username': 'sneha_patel', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'sneha-patel'), 'first_name': 'Sneha', 'last_name': 'Patel', 'skills': ['Figma', 'UI/UX Design']},
            {'username': 'arjun_singh', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'arjun-singh'), 'first_name': 'Arjun', 'last_name': 'Singh', 'skills': ['JavaScript', 'React', 'TypeScript']},
            {'username': 'kavya_nair', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'kavya-nair'), 'first_name': 'Kavya', 'last_name': 'Nair', 'skills': ['Machine Learning', 'Data Science', 'Python']},
            {'username': 'vikram_mehta', 'email': _gmail_alias(PRIMARY_DEMO_INBOX, 'vikram-mehta'), 'first_name': 'Vikram', 'last_name': 'Mehta', 'skills': ['Docker', 'Kubernetes', 'AWS', 'DevOps']},
        ]
        
        for cand in new_candidates:
            user, created = User.objects.get_or_create(
                username=cand['username'],
                defaults={
                    'email': cand['email'],
                    'first_name': cand['first_name'],
                    'last_name': cand['last_name'],
                    'role': 'user',
                    'email_verified': True,
                    'bio': f"Experienced professional specializing in {', '.join(cand['skills'])}.",
                }
            )
            user.email = cand['email']
            user.first_name = cand['first_name']
            user.last_name = cand['last_name']
            user.role = 'user'
            user.email_verified = True
            user.bio = f"Experienced professional specializing in {', '.join(cand['skills'])}."
            user.set_password('demo1234')
            user.save()
            if created:
                for s in cand['skills']:
                     if s in skills:
                         user.skills.add(skills[s])
        self.stdout.write(f'  Created {len(new_candidates)} additional candidates')

        # ── Job Applications (Fake PDF) ─────────────────────
        # Minimal valid PDF (~200 bytes)
        fake_pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 <<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\n>>\n>>\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 55\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(TalentOrbit Demo Resume) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000109 00000 n \n0000000266 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n370\n%%EOF'

        all_candidates = User.objects.filter(role='user')
        all_jobs = Job.objects.filter(is_active=True)
        
        if all_candidates.exists() and all_jobs.exists():
            # Create ~10 applications
            import random
            from django.core.files.base import ContentFile
            # JobApplication is already imported from core.models
            apps_created = 0
            for i in range(15):
                applicant = random.choice(all_candidates)
                job = random.choice(all_jobs)
                
                if not JobApplication.objects.filter(job=job, applicant=applicant).exists():
                    status = random.choice(['pending', 'reviewed', 'shortlisted', 'rejected'])
                    app = JobApplication(
                        job=job,
                        applicant=applicant,
                        cover_letter=f"I am very interested in this {job.title} position. I have the required skills and experience.",
                        status=status,
                        applied_at=timezone.now() - timedelta(days=random.randint(0, 10))
                    )
                    # Create a file name
                    filename = f"resume_{applicant.username}_{job.pk}.pdf"
                    app.resume.save(filename, ContentFile(fake_pdf_content), save=False)
                    app.save()
                    apps_created += 1
            self.stdout.write(f'  Created {apps_created} job applications')

        self.stdout.write(self.style.SUCCESS('Done! Mock data seeded successfully.'))
        self.stdout.write(f'  Demo login: any company username (e.g. techcorp) / password: demo1234')
        self.stdout.write(f'  Demo user: john_doe / demo1234')
        # ── Saved Jobs ──────────────────────────────────────
        all_users = User.objects.filter(role='user')
        if all_jobs.exists() and all_users.exists():
            import random
            count = 0
            for i in range(10):
                u = random.choice(all_users)
                j = random.choice(all_jobs)
                if not SavedJob.objects.filter(user=u, job=j).exists():
                    SavedJob.objects.create(user=u, job=j)
                    count += 1
            self.stdout.write(f'  Created {count} saved jobs')

        # ── Tenders & Bids ──────────────────────────────────
        techcorp = company_profiles.get('TechCorp Solutions')
        designhub = company_profiles.get('DesignHub Studio')
        nexasoft = company_profiles.get('NexaSoft Technologies')

        if techcorp and designhub and nexasoft:
            # Tender 1
            t1, _ = Tender.objects.get_or_create(
                title='Corporate Rebranding Project',
                posted_by=techcorp,
                defaults={
                    'description': 'Complete overhaul of our brand identity including logo, guidelines, and website redesign.',
                    'budget': 750000,
                    'deadline': now.date() + timedelta(days=15),
                    'status': 'open'
                }
            )
            # Bid on T1
            if not TenderBid.objects.filter(tender=t1, bidder=designhub).exists():
                TenderBid.objects.create(
                    tender=t1,
                    bidder=designhub,
                    proposal='We are experts in rebranding. See our portfolio attached.',
                    amount=750000
                )

            # Tender 2
            t2, _ = Tender.objects.get_or_create(
                title='Banking API Integration',
                posted_by=nexasoft,
                defaults={
                    'description': 'Integration of unified payment interface into our core banking core.',
                    'budget': 2000000,
                    'deadline': now.date() + timedelta(days=20),
                    'status': 'open'
                }
            )
            
            self.stdout.write('  Created Tenders and Bids')

        # ── Quizzes ─────────────────────────────────────────
        quizzes_data = [
            {'title': 'Python Fundamentals', 'cat': 'Software Development', 'time': 20, 'pass': 60, 'qs': [
                ('What is the output of print(2 ** 3)?', '8', ['6', '8', '9', '23']),
                ('Which keyword is used to define a function?', 'def', ['func', 'define', 'def', 'lambda']),
                ('What data type is [1, 2, 3]?', 'List', ['Tuple', 'List', 'Set', 'Dictionary']),
                ('How do you insert comments in Python?', '#', ['//', '/*', '#', '<!--']),
                ('Which method adds an element to a list?', 'append()', ['add()', 'push()', 'append()', 'insert()']),
            ]},
            {'title': 'Web Development Basics', 'cat': 'Software Development', 'time': 15, 'pass': 60, 'qs': [
                ('What does HTML stand for?', 'Hyper Text Markup Language', ['Hyper Text Markup Language', 'High Text Markup Language', 'Hyper Tabular Markup Language', 'Hyper Tool Markup Language']),
                ('Which tag is used for the largest heading?', '<h1>', ['<h6>', '<head>', '<h1>', '<header>']),
                ('What is the correct HTML element for inserting a line break?', '<br>', ['<lb>', '<break>', '<br>', '<newline>']),
                ('Which CSS property controls text size?', 'font-size', ['text-style', 'font-size', 'text-size', 'font-style']),
                ('Inside which HTML element do we put the JavaScript?', '<script>', ['<js>', '<javascript>', '<script>', '<code>']),
            ]},
            {'title': 'Data Science Essentials', 'cat': 'Data Science & AI', 'time': 25, 'pass': 70, 'qs': [
                ('Which library is used for data manipulation?', 'Pandas', ['Numpy', 'Pandas', 'Matplotlib', 'Scikit-learn']),
                ('What does CSV stand for?', 'Comma Separated Values', ['Common Separated Values', 'Comma Separated Values', 'Computer Separated Values', 'Cascading Style Values']),
                ('Which model is used for classification?', 'Logistic Regression', ['Linear Regression', 'Logistic Regression', 'K-Means', 'Decision Tree']),
                ('What is checking accuracy on unseen data called?', 'Testing', ['Training', 'Validation', 'Testing', 'Debugging']),
                ('Which plot creates a distribution chart?', 'Histogram', ['Scatter', 'Line', 'Histogram', 'Bar']),
            ]},
            {'title': 'Data Science Basics', 'cat': 'Data Science & AI', 'time': 45, 'pass': 70, 'qs': [
                ('What is the first step in data analysis?', 'Data Cleaning', ['Data Cleaning', 'Modeling', 'Visualization', 'Deployment']),
                ('Which library is used for data manipulation in Python?', 'Pandas', ['Numpy', 'Pandas', 'Matplotlib', 'Scikit-learn']),
                ('What is checking accuracy on unseen data called?', 'Testing', ['Training', 'Validation', 'Testing', 'Debugging']),
                ('Which plot creates a distribution chart?', 'Histogram', ['Scatter', 'Line', 'Histogram', 'Bar']),
            ]},
        ]

        for qd in quizzes_data:
            cat = cats.get(qd['cat'])
            if cat:
                quiz, _ = Quiz.objects.get_or_create(
                    title=qd['title'],
                    defaults={
                        'category': cat,
                        'description': f"Test your knowledge of {qd['title']}.",
                        'time_limit': qd['time'],
                        'passing_score': qd['pass'],
                        'is_active': True
                    }
                )
                
                # Add questions
                if quiz.questions.count() == 0:
                    for txt, corr_text, opts in qd['qs']:
                        # Find which index (0-3) matches the correct text
                        try:
                            idx = opts.index(corr_text)
                            letter = ['A', 'B', 'C', 'D'][idx]
                        except ValueError:
                            letter = 'A' # Fallback

                        QuizQuestion.objects.create(
                            quiz=quiz,
                            question_text=txt,
                            option_a=opts[0],
                            option_b=opts[1],
                            option_c=opts[2],
                            option_d=opts[3],
                            correct_option=letter,
                            order=0
                        )
        self.stdout.write(f'  Created {len(quizzes_data)} quizzes')

        # ── Skill Videos ─────────────────────────────────────
        fake_mp4_content = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'
        video_seed = [
            {
                'title': 'Python Interview Basics',
                'description': 'Introductory guidance for Python interview preparation.',
                'category': cats.get('Software Development'),
                'duration': '08:12',
                'is_premium': True,
                'filename': 'python-interview-basics.mp4',
            },
            {
                'title': 'Design Portfolio Review Tips',
                'description': 'How to present case studies and improve your portfolio walkthrough.',
                'category': cats.get('Design & Creative'),
                'duration': '06:40',
                'is_premium': False,
                'filename': 'design-portfolio-review.mp4',
            },
        ]
        video_count = 0
        for vd in video_seed:
            video, created = SkillVideo.objects.get_or_create(
                title=vd['title'],
                defaults={
                    'description': vd['description'],
                    'category': vd['category'],
                    'duration': vd['duration'],
                    'is_premium': vd['is_premium'],
                    'uploaded_by': admin,
                }
            )
            if created or not video.video_file:
                video.description = vd['description']
                video.category = vd['category']
                video.duration = vd['duration']
                video.is_premium = vd['is_premium']
                video.uploaded_by = admin
                video.video_file.save(vd['filename'], ContentFile(fake_mp4_content), save=False)
                video.save()
                video_count += 1
        self.stdout.write(f'  Created {len(video_seed)} skill videos ({video_count} new files)')

        # Quiz Attempts
        if all_users.exists():
            u = all_users.first()
            q = Quiz.objects.first()
            if u and q and not QuizAttempt.objects.filter(user=u, quiz=q).exists():
                QuizAttempt.objects.create(
                    user=u, quiz=q, score=4, total_questions=5, percentage=80.0, passed=True, completed_at=now
                )
            self.stdout.write('  Created Quiz Attempts')

        # ── Subscriptions ───────────────────────────────────
        sub_plans = [
            ('monthly', 299, 30),
            ('quarterly', 799, 90),
            ('yearly', 2499, 365),
        ]
        import random
        for _ in range(3):
            u = random.choice(all_candidates)
            if not Subscription.objects.filter(user=u, is_active=True).exists():
                plan, amt, days = random.choice(sub_plans)
                Subscription.objects.create(
                    user=u,
                    plan=plan,
                    amount=amt,
                    expires_at=now + timedelta(days=days),
                    is_active=True,
                    razorpay_payment_id=f'pay_fake_{random.randint(1000,9999)}'
                )
                u.is_subscribed = True
                u.subscription_expiry = now + timedelta(days=days)
                u.save(update_fields=['is_subscribed', 'subscription_expiry'])
        self.stdout.write('  Created Subscriptions')

        # ── Notifications ───────────────────────────────────
        for u in all_candidates[:3]:
             if not Notification.objects.filter(recipient=u).exists():
                 Notification.objects.create(
                     recipient=u,
                     title='Welcome to TalentOrbit',
                     message='Complete your profile to get better job recommendations.',
                     notif_type='system'
                 )
        self.stdout.write('  Created Notifications')

        # ── Newsletter ──────────────────────────────────────
        emails = [
            _gmail_alias(PRIMARY_DEMO_INBOX, 'newsletter-news-1'),
            _gmail_alias(PRIMARY_DEMO_INBOX, 'newsletter-subscriber'),
            _gmail_alias(PRIMARY_DEMO_INBOX, 'newsletter-hello'),
        ]
        for e in emails:
            NewsletterSubscription.objects.get_or_create(email=e)
        self.stdout.write('  Created Newsletter Subscriptions')
