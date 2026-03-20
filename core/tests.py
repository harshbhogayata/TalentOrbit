"""
TalentOrbit Test Suite
======================
Covers models, auth, access control, views, and security.
Run with: python manage.py test core
"""

from datetime import timedelta
from io import StringIO
from pathlib import Path
from smtplib import SMTPServerDisconnected
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import json

from .utils import EmailDeliveryResult

from .models import (
    User, CompanyProfile, JobCategory, Job, JobApplication, Skill, Tender, TenderBid,
    Subscription, Notification, Quiz, QuizQuestion, QuizAttempt,
    SavedJob, NewsletterSubscription,
)


# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────

def _create_user(username='testuser', email='test@example.com',
                 role='user', password='Str0ngP@ss!'):
    return User.objects.create_user(
        username=username, email=email, role=role, password=password,
        email_verified=True,  # Test users are pre-verified
    )


def _create_company_user(username='companyuser', email='company@example.com',
                         password='Str0ngP@ss!'):
    user = _create_user(username=username, email=email, role='company', password=password)
    profile = CompanyProfile.objects.create(
        user=user, company_name='TestCorp', status='approved',
    )
    return user, profile


def _create_admin(username='adminuser', email='admin@example.com',
                  password='Str0ngP@ss!'):
    return _create_user(username=username, email=email, role='admin', password=password)


# ──────────────────────────────────────────────────────────────
#  MODEL TESTS
# ──────────────────────────────────────────────────────────────

class UserModelTests(TestCase):

    def test_user_creation_with_role(self):
        user = _create_user()
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_regular_user)
        self.assertFalse(user.is_admin_user)
        self.assertFalse(user.is_company_user)

    def test_subscription_active_false_by_default(self):
        user = _create_user()
        self.assertFalse(user.subscription_active)

    def test_subscription_active_true_when_valid(self):
        user = _create_user()
        user.is_subscribed = True
        user.subscription_expiry = timezone.now() + timedelta(days=30)
        user.save()
        self.assertTrue(user.subscription_active)

    def test_subscription_active_false_when_expired(self):
        user = _create_user()
        user.is_subscribed = True
        user.subscription_expiry = timezone.now() - timedelta(days=1)
        user.save()
        self.assertFalse(user.subscription_active)

    def test_email_uniqueness(self):
        _create_user(username='a', email='dupe@example.com')
        with self.assertRaises(Exception):
            _create_user(username='b', email='dupe@example.com')


class JobModelTests(TestCase):

    def test_is_expired_past_deadline(self):
        user, profile = _create_company_user()
        job = Job.objects.create(
            company=profile, title='Old Job', description='desc',
            deadline=timezone.now().date() - timedelta(days=1),
        )
        self.assertTrue(job.is_expired)

    def test_is_expired_no_deadline(self):
        user, profile = _create_company_user()
        job = Job.objects.create(
            company=profile, title='No Deadline', description='desc',
        )
        self.assertFalse(job.is_expired)

    def test_is_expired_future_deadline(self):
        user, profile = _create_company_user()
        job = Job.objects.create(
            company=profile, title='Future', description='desc',
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.assertFalse(job.is_expired)


# ──────────────────────────────────────────────────────────────
#  AUTH TESTS
# ──────────────────────────────────────────────────────────────

class RegistrationTests(TestCase):

    def setUp(self):
        # Clear rate-limiter's in-memory cache so previous test
        # POSTs to /register/ don't trigger 429 in this test.
        from .middleware import RateLimitMiddleware
        RateLimitMiddleware._requests.clear()

    def test_user_registration(self):
        resp = self.client.post(reverse('register_user'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_company_registration(self):
        resp = self.client.post(reverse('register_company'), {
            'username': 'newcorp',
            'email': 'corp@example.com',
            'company_name': 'NewCorp',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username='newcorp')
        self.assertEqual(user.role, 'company')
        self.assertTrue(CompanyProfile.objects.filter(user=user).exists())

    def test_duplicate_email_rejected(self):
        _create_user(username='existing', email='taken@example.com')
        resp = self.client.post(reverse('register_user'), {
            'username': 'another',
            'email': 'taken@example.com',
            'first_name': 'A',
            'last_name': 'B',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        # Should re-render the form (200) with an error, not redirect
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='another').exists())


class LoginTests(TestCase):

    def test_login_with_username(self):
        _create_user(username='logintest', email='login@example.com')
        resp = self.client.post(reverse('login'), {
            'username': 'logintest',
            'password': 'Str0ngP@ss!',
        })
        self.assertEqual(resp.status_code, 302)

    def test_login_with_email(self):
        _create_user(username='emaillogin', email='emaillogin@example.com')
        resp = self.client.post(reverse('login'), {
            'username': 'emaillogin@example.com',
            'password': 'Str0ngP@ss!',
        })
        self.assertEqual(resp.status_code, 302)

    def test_password_reset_page_loads(self):
        resp = self.client.get(reverse('password_reset'))
        self.assertEqual(resp.status_code, 200)


# ──────────────────────────────────────────────────────────────
#  ACCESS CONTROL TESTS
# ──────────────────────────────────────────────────────────────

class AccessControlTests(TestCase):

    def test_unauthenticated_redirect_to_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_user_cannot_access_admin_panel(self):
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 302)  # redirected away

    def test_user_cannot_access_company_pages(self):
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('company_manage_jobs'))
        self.assertEqual(resp.status_code, 302)

    def test_admin_can_access_admin_panel(self):
        admin = _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_download_admin_report(self):
        _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('admin_download_report'))
        self.assertEqual(resp.status_code, 302)

    def test_company_can_access_company_dashboard(self):
        user, _ = _create_company_user()
        self.client.login(username='companyuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)


class AdminPanelCreateTests(TestCase):
    def setUp(self):
        _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')

    def test_admin_create_user_page_loads(self):
        resp = self.client.get(reverse('admin_create_user'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_create_user_post(self):
        resp = self.client.post(reverse('admin_create_user'), {
            'username': 'paneluser',
            'first_name': 'Panel',
            'last_name': 'User',
            'email': 'paneluser@example.com',
            'phone': '9999999999',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
            'email_verified': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username='paneluser')
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.email_verified)

    def test_admin_create_company_page_loads(self):
        resp = self.client.get(reverse('admin_create_company'))
        self.assertEqual(resp.status_code, 200)

    def test_admin_create_company_post(self):
        resp = self.client.post(reverse('admin_create_company'), {
            'username': 'panelcompany',
            'email': 'panelcompany@example.com',
            'company_name': 'Panel Company',
            'industry': 'IT',
            'website': 'https://panel.example.com',
            'description': 'Created by admin.',
            'status': 'approved',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
            'email_verified': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username='panelcompany')
        self.assertEqual(user.role, 'company')
        self.assertTrue(user.email_verified)
        self.assertEqual(user.company_profile.company_name, 'Panel Company')
        self.assertEqual(user.company_profile.status, 'approved')


# ──────────────────────────────────────────────────────────────
#  VIEW TESTS
# ──────────────────────────────────────────────────────────────

class CompanyJobManagementTests(TestCase):
    def setUp(self):
        self.user, self.profile = _create_company_user()
        self.category = JobCategory.objects.create(name='Engineering', slug='engineering')
        self.client.login(username='companyuser', password='Str0ngP@ss!')

    def test_company_can_post_job_with_existing_category(self):
        resp = self.client.post(reverse('company_post_job'), {
            'title': 'Backend Engineer',
            'category': self.category.pk,
            'description': 'Build APIs',
            'requirements': 'Django experience',
            'job_type': 'full_time',
            'experience': '3-5',
            'salary_min': '80000',
            'salary_max': '120000',
            'location': 'Remote',
            'skills': 'Python, Django',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat(),
        })
        self.assertRedirects(resp, reverse('company_manage_jobs'))
        job = Job.objects.get(title='Backend Engineer')
        self.assertEqual(job.company, self.profile)
        self.assertEqual(job.category, self.category)
        self.assertSetEqual(set(job.skills.values_list('name', flat=True)), {'Python', 'Django'})

    def test_company_can_post_job_with_new_category(self):
        resp = self.client.post(reverse('company_post_job'), {
            'title': 'Platform Engineer',
            'category': '',
            'new_category': 'Platform Engineering',
            'description': 'Own deployment platform',
            'requirements': 'CI/CD experience',
            'job_type': 'full_time',
            'experience': '3-5',
            'salary_min': '100000',
            'salary_max': '150000',
            'location': 'Bengaluru',
            'skills': 'Kubernetes, Terraform',
            'deadline': (timezone.now().date() + timedelta(days=45)).isoformat(),
        })
        self.assertRedirects(resp, reverse('company_manage_jobs'))
        job = Job.objects.get(title='Platform Engineer')
        self.assertEqual(job.company, self.profile)
        self.assertEqual(job.category.name, 'Platform Engineering')

    def test_company_post_job_requires_category_or_new_category(self):
        resp = self.client.post(reverse('company_post_job'), {
            'title': 'Uncategorized Job',
            'category': '',
            'new_category': '',
            'description': 'Missing category',
            'requirements': 'None',
            'job_type': 'full_time',
            'experience': '1-2',
            'salary_min': '50000',
            'salary_max': '80000',
            'location': 'Remote',
            'skills': 'SQL',
            'deadline': (timezone.now().date() + timedelta(days=20)).isoformat(),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Select a category or enter a new one.')
        self.assertFalse(Job.objects.filter(title='Uncategorized Job').exists())


class CompanyTenderManagementTests(TestCase):
    def setUp(self):
        self.user, self.profile = _create_company_user()
        self.other_user, self.other_profile = _create_company_user(
            username='othercompany',
            email='othercompany@example.com',
        )
        self.client.login(username='companyuser', password='Str0ngP@ss!')

    def test_company_can_create_tender(self):
        resp = self.client.post(reverse('company_create_tender'), {
            'title': 'Infrastructure Refresh',
            'description': 'Modernize our cloud stack.',
            'budget': '500000',
            'deadline': (timezone.now().date() + timedelta(days=21)).isoformat(),
            'requirements': 'Cloud migration experience',
        })
        self.assertRedirects(resp, reverse('company_tenders'))
        tender = Tender.objects.get(title='Infrastructure Refresh')
        self.assertEqual(tender.posted_by, self.profile)

    def test_company_can_delete_own_tender(self):
        tender = Tender.objects.create(
            posted_by=self.profile,
            title='Delete Me',
            description='Disposable tender',
            deadline=timezone.now().date() + timedelta(days=10),
        )
        TenderBid.objects.create(
            tender=tender,
            bidder=self.other_profile,
            amount='12345',
            proposal='Bid proposal',
        )
        resp = self.client.post(reverse('company_delete_tender', args=[tender.pk]))
        self.assertRedirects(resp, reverse('company_tenders'))
        self.assertFalse(Tender.objects.filter(pk=tender.pk).exists())
        self.assertFalse(TenderBid.objects.filter(tender_id=tender.pk).exists())

    def test_company_cannot_delete_other_company_tender(self):
        tender = Tender.objects.create(
            posted_by=self.other_profile,
            title='Protected Tender',
            description='Owned by another company',
            deadline=timezone.now().date() + timedelta(days=10),
        )
        resp = self.client.post(reverse('company_delete_tender', args=[tender.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Tender.objects.filter(pk=tender.pk).exists())


class PublicViewTests(TestCase):
    def setUp(self):
        company_user, company_profile = _create_company_user()
        category = JobCategory.objects.create(name='Engineering', slug='engineering')
        self.job = Job.objects.create(
            company=company_profile,
            category=category,
            title='Platform Engineer',
            description='Build platform features',
            is_active=True,
            deadline=timezone.now().date() + timedelta(days=14),
        )

    def test_home_page(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)

    def test_job_list_page(self):
        resp = self.client.get(reverse('job_list'))
        self.assertEqual(resp.status_code, 200)

    def test_job_detail_page(self):
        resp = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'jobs/job_detail.html')

    def test_company_list_page(self):
        resp = self.client.get(reverse('company_list'))
        self.assertEqual(resp.status_code, 200)

    def test_about_page(self):
        resp = self.client.get(reverse('about'))
        self.assertEqual(resp.status_code, 200)

    def test_contact_page(self):
        resp = self.client.get(reverse('contact'))
        self.assertEqual(resp.status_code, 200)


class UserJobWorkspaceTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        company_user, company_profile = _create_company_user(
            username='jobscompany',
            email='jobscompany@example.com',
        )
        category = JobCategory.objects.create(name='Product', slug='product')
        self.job = Job.objects.create(
            company=company_profile,
            category=category,
            title='Product Analyst',
            description='Analyze customer journeys',
            is_active=True,
            deadline=timezone.now().date() + timedelta(days=21),
        )
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_authenticated_user_job_list_uses_workspace_template(self):
        resp = self.client.get(reverse('job_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'user/job_list.html')

    def test_authenticated_user_job_detail_uses_workspace_template(self):
        resp = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'user/job_detail.html')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetEmailTemplateTests(TestCase):
    def test_password_reset_email_uses_full_name_and_renders_html(self):
        user = _create_user(username='grace', email='grace@example.com')
        user.first_name = 'Grace'
        user.last_name = 'Hopper'
        user.save(update_fields=['first_name', 'last_name'])

        resp = self.client.post(reverse('password_reset'), {'email': user.email})

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Hi Grace Hopper,', mail.outbox[0].body)
        self.assertNotIn('{{ user.get_full_name', mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        html_body = mail.outbox[0].alternatives[0][0]
        self.assertIn('Hi Grace Hopper,', html_body)
        self.assertNotIn('{{ user.get_full_name', html_body)

    def test_password_reset_email_falls_back_to_generic_greeting(self):
        user = _create_user(username='nogreeting', email='nogreeting@example.com')

        self.client.post(reverse('password_reset'), {'email': user.email})

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Hi there,', mail.outbox[0].body)
        self.assertNotIn(f'Hi {user.username},', mail.outbox[0].body)
        html_body = mail.outbox[0].alternatives[0][0]
        self.assertIn('Hi there,', html_body)
        self.assertNotIn(f'Hi {user.username},', html_body)


class SubscriptionViewTests(TestCase):

    def test_subscribe_requires_post(self):
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('subscribe', args=['monthly']))
        self.assertEqual(resp.status_code, 302)  # redirects, no state change
        user.refresh_from_db()
        self.assertFalse(user.is_subscribed)

    def test_subscribe_post_requires_checkout(self):
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.post(reverse('subscribe', args=['monthly']), follow=True)
        self.assertRedirects(resp, reverse('subscription_page'))
        user.refresh_from_db()
        self.assertFalse(user.is_subscribed)
        messages = [str(message) for message in resp.context['messages']]
        self.assertTrue(any('checkout' in message.lower() for message in messages))


class QuizViewTests(TestCase):

    def _setup_quiz(self):
        user, profile = _create_company_user()
        cat = JobCategory.objects.create(name='Tech', slug='tech')
        quiz = Quiz.objects.create(
            title='Test Quiz', time_limit=30, passing_score=50, is_active=True,
            category=cat,
        )
        q1 = QuizQuestion.objects.create(
            quiz=quiz, question_text='What is 1+1?',
            option_a='1', option_b='2', option_c='3', option_d='4',
            correct_option='B', order=1,
        )
        return quiz, q1

    def test_quiz_post_calculates_score(self):
        quiz, q1 = self._setup_quiz()
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.post(reverse('take_quiz', args=[quiz.pk]), {
            f'question_{q1.pk}': 'B',
            'started_at': timezone.now().isoformat(),
        })
        self.assertEqual(resp.status_code, 200)
        attempt = QuizAttempt.objects.get(user=user, quiz=quiz)
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.percentage, 100.0)
        self.assertTrue(attempt.passed)

    def test_quiz_wrong_answer(self):
        quiz, q1 = self._setup_quiz()
        user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.post(reverse('take_quiz', args=[quiz.pk]), {
            f'question_{q1.pk}': 'A',
            'started_at': timezone.now().isoformat(),
        })
        attempt = QuizAttempt.objects.get(user=user, quiz=quiz)
        self.assertEqual(attempt.score, 0)
        self.assertFalse(attempt.passed)


# ──────────────────────────────────────────────────────────────
#  SECURITY TESTS
# ──────────────────────────────────────────────────────────────

class SecurityTests(TestCase):
    """Verify all state-mutating endpoints reject GET requests."""

    def setUp(self):
        self.admin = _create_admin()
        self.user = _create_user(username='secuser', email='sec@example.com')
        self.company_user, self.company_profile = _create_company_user(
            username='seccompany', email='seccomp@example.com',
        )

    def test_approve_company_rejects_get(self):
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        profile = CompanyProfile.objects.create(
            user=_create_user(username='pending', email='pending@example.com', role='company'),
            company_name='PendingCorp', status='pending',
        )
        resp = self.client.get(reverse('admin_approve_company', args=[profile.pk]))
        self.assertEqual(resp.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.status, 'pending')  # unchanged

    def test_reject_company_rejects_get(self):
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        profile = CompanyProfile.objects.create(
            user=_create_user(username='pending2', email='pending2@example.com', role='company'),
            company_name='PendingCorp2', status='pending',
        )
        resp = self.client.get(reverse('admin_reject_company', args=[profile.pk]))
        self.assertEqual(resp.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.status, 'pending')

    def test_subscribe_rejects_get(self):
        self.client.login(username='secuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('subscribe', args=['monthly']))
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_subscribed)

    def test_logout_rejects_get(self):
        self.client.login(username='secuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        # User should still be logged in (GET was rejected)
        resp2 = self.client.get(reverse('dashboard'))
        self.assertEqual(resp2.status_code, 200)

    def test_mark_all_read_rejects_get(self):
        self.client.login(username='secuser', password='Str0ngP@ss!')
        Notification.objects.create(
            recipient=self.user, title='Test', message='msg',
        )
        resp = self.client.get(reverse('mark_all_read'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            Notification.objects.filter(recipient=self.user, is_read=False).count(), 1,
        )

    def test_notifications_uses_user_sidebar_for_users(self):
        self.client.login(username='secuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('notifications'))
        self.assertContains(resp, 'Subscription')
        self.assertNotContains(resp, 'Create Tender')

    def test_notifications_uses_company_sidebar_for_companies(self):
        company_user = _create_user(
            username='notifcompany',
            email='notifcompany@example.com',
            role='company',
        )
        CompanyProfile.objects.create(
            user=company_user,
            company_name='Notif Company',
            status='approved',
        )
        self.client.login(username='notifcompany', password='Str0ngP@ss!')
        resp = self.client.get(reverse('notifications'))
        self.assertContains(resp, 'Create Tender')
        self.assertNotContains(resp, 'Subscription')

    def test_notifications_uses_admin_sidebar_for_admins(self):
        _create_admin(username='notifadmin', email='notifadmin@example.com')
        self.client.login(username='notifadmin', password='Str0ngP@ss!')
        resp = self.client.get(reverse('notifications'))
        self.assertContains(resp, 'Send Alerts')
        self.assertContains(resp, 'Companies')
        self.assertNotContains(resp, 'Create Tender')

    def test_csp_header_present(self):
        resp = self.client.get(reverse('home'))
        self.assertIn('Content-Security-Policy', resp)


class RateLimitTests(TestCase):
    """Verify the rate limiter returns 429 after too many requests."""

    def test_login_rate_limit(self):
        # The limit is 5 POSTs per 60 seconds
        for _ in range(5):
            self.client.post(reverse('login'), {
                'username': 'nobody', 'password': 'wrong',
            })
        resp = self.client.post(reverse('login'), {
            'username': 'nobody', 'password': 'wrong',
        })
        self.assertEqual(resp.status_code, 429)


# ──────────────────────────────────────────────────────────────
#  NEW TESTS — Round 3 Features
# ──────────────────────────────────────────────────────────────

class SubscriptionExpiryTests(TestCase):
    """Test subscription auto-reset on expiry."""

    def test_subscription_active_resets_is_subscribed_on_expiry(self):
        user = _create_user()
        user.is_subscribed = True
        user.subscription_expiry = timezone.now() - timedelta(days=1)
        user.save()
        # Access the property — should auto-reset is_subscribed
        self.assertFalse(user.subscription_active)
        user.refresh_from_db()
        self.assertFalse(user.is_subscribed)

    def test_subscription_active_does_not_reset_valid(self):
        user = _create_user()
        user.is_subscribed = True
        user.subscription_expiry = timezone.now() + timedelta(days=30)
        user.save()
        self.assertTrue(user.subscription_active)
        user.refresh_from_db()
        self.assertTrue(user.is_subscribed)


class SavedJobTests(TestCase):
    """Test job bookmark toggle."""

    def setUp(self):
        self.user = _create_user()
        _, self.profile = _create_company_user()
        self.job = Job.objects.create(
            company=self.profile, title='Saved Test', description='desc',
        )
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_toggle_save_creates_bookmark(self):
        resp = self.client.post(reverse('toggle_save_job', args=[self.job.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SavedJob.objects.filter(user=self.user, job=self.job).exists())

    def test_toggle_save_removes_bookmark(self):
        SavedJob.objects.create(user=self.user, job=self.job)
        resp = self.client.post(reverse('toggle_save_job', args=[self.job.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SavedJob.objects.filter(user=self.user, job=self.job).exists())

    def test_saved_jobs_page_loads(self):
        resp = self.client.get(reverse('saved_jobs'))
        self.assertEqual(resp.status_code, 200)

    def test_toggle_save_rejects_get(self):
        resp = self.client.get(reverse('toggle_save_job', args=[self.job.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SavedJob.objects.filter(user=self.user, job=self.job).exists())


class AdminEditCategoryTests(TestCase):
    """Test admin category editing."""

    def setUp(self):
        self.admin = _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        self.cat = JobCategory.objects.create(
            name='OldName', slug='oldname', icon='bi-briefcase',
        )

    def test_edit_category_get(self):
        resp = self.client.get(reverse('admin_edit_category', args=[self.cat.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_edit_category_post(self):
        resp = self.client.post(reverse('admin_edit_category', args=[self.cat.pk]), {
            'name': 'NewName',
            'slug': 'newname',
            'icon': 'bi-code',
            'description': 'Updated',
            'is_active': True,
        })
        self.assertEqual(resp.status_code, 302)
        self.cat.refresh_from_db()
        self.assertEqual(self.cat.name, 'NewName')
        self.assertEqual(self.cat.icon, 'bi-code')


class AdminQuizQuestionTests(TestCase):
    """Test admin quiz question edit/delete."""

    def setUp(self):
        self.admin = _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        self.quiz = Quiz.objects.create(
            title='Test Quiz', time_limit=30, passing_score=50, is_active=True,
        )
        self.question = QuizQuestion.objects.create(
            quiz=self.quiz, question_text='Q?',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_option='A', order=1,
        )

    def test_edit_question_get(self):
        resp = self.client.get(reverse('admin_edit_question', args=[self.question.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_edit_question_post(self):
        resp = self.client.post(reverse('admin_edit_question', args=[self.question.pk]), {
            'question_text': 'Updated?',
            'option_a': 'X', 'option_b': 'Y', 'option_c': 'Z', 'option_d': 'W',
            'correct_option': 'B', 'order': 2,
        })
        self.assertEqual(resp.status_code, 302)
        self.question.refresh_from_db()
        self.assertEqual(self.question.question_text, 'Updated?')
        self.assertEqual(self.question.correct_option, 'B')

    def test_delete_question_post(self):
        resp = self.client.post(reverse('admin_delete_question', args=[self.question.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(QuizQuestion.objects.filter(pk=self.question.pk).exists())

    def test_delete_question_rejects_get(self):
        resp = self.client.get(reverse('admin_delete_question', args=[self.question.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(QuizQuestion.objects.filter(pk=self.question.pk).exists())


# ──────────────────────────────────────────────────────────────
#  EMAIL VERIFICATION TESTS
# ──────────────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailVerificationTests(TestCase):
    """Test email verification flow."""

    def setUp(self):
        from .middleware import RateLimitMiddleware
        RateLimitMiddleware._requests.clear()

    def test_registration_redirects_to_verification_sent(self):
        """After registration, user should be redirected to verification-sent page."""
        resp = self.client.post(reverse('register_user'), {
            'username': 'verifyuser',
            'email': 'verify@example.com',
            'first_name': 'Verify',
            'last_name': 'User',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertRedirects(resp, reverse('verification_sent'))

    def test_registration_sends_verification_email(self):
        self.client.post(reverse('register_user'), {
            'username': 'verifymail',
            'email': 'verifymail@example.com',
            'first_name': 'Verify',
            'last_name': 'Mail',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['verifymail@example.com'])
        self.assertIn('/verify-email/', mail.outbox[0].body)

    def test_registration_stores_pending_user_for_resend(self):
        self.client.post(reverse('register_user'), {
            'username': 'sessionverify',
            'email': 'sessionverify@example.com',
            'first_name': 'Session',
            'last_name': 'Verify',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        user = User.objects.get(username='sessionverify')
        self.assertEqual(self.client.session.get('unverified_user_pk'), user.pk)
        verification_state = self.client.session.get('verification_email_state')
        self.assertEqual(verification_state['email'], 'sessionverify@example.com')
        self.assertTrue(verification_state['last_attempt_ok'])

    @override_settings(PUBLIC_APP_URL='https://app.talentorbit.test')
    def test_verification_email_uses_public_app_url_when_configured(self):
        self.client.post(reverse('register_user'), {
            'username': 'publicurluser',
            'email': 'publicurl@example.com',
            'first_name': 'Public',
            'last_name': 'Url',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertIn('https://app.talentorbit.test/verify-email/', mail.outbox[-1].body)

    def test_verification_sent_page_shows_target_email(self):
        resp = self.client.post(reverse('register_user'), {
            'username': 'verifypage',
            'email': 'verifypage@example.com',
            'first_name': 'Verify',
            'last_name': 'Page',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        }, follow=True)
        self.assertContains(resp, 'verifypage@example.com')
        self.assertContains(resp, 'Check Your Email')

    @patch('core.utils.time.sleep', return_value=None)
    @patch('core.utils.django_send_mail', side_effect=[SMTPServerDisconnected('connection lost'), 1])
    def test_registration_retries_transient_email_failures(self, mock_send_mail, _mock_sleep):
        resp = self.client.post(reverse('register_user'), {
            'username': 'retryverify',
            'email': 'retryverify@example.com',
            'first_name': 'Retry',
            'last_name': 'Verify',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        }, follow=True)
        self.assertContains(resp, 'Check Your Email')
        self.assertEqual(mock_send_mail.call_count, 2)
        verification_state = self.client.session.get('verification_email_state')
        self.assertTrue(verification_state['last_attempt_ok'])
        self.assertEqual(verification_state['last_error_code'], '')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_registration_detects_non_delivering_email_backend(self):
        resp = self.client.post(reverse('register_user'), {
            'username': 'consoleverify',
            'email': 'consoleverify@example.com',
            'first_name': 'Console',
            'last_name': 'Verify',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        }, follow=True)
        self.assertContains(resp, 'Verification Email Is Not Configured')
        verification_state = self.client.session.get('verification_email_state')
        self.assertFalse(verification_state['last_attempt_ok'])
        self.assertEqual(verification_state['last_error_code'], 'email_backend_not_configured')

    @override_settings(PUBLIC_APP_URL='not-a-valid-url')
    def test_invalid_public_app_url_blocks_verification_email(self):
        resp = self.client.post(reverse('register_user'), {
            'username': 'badpublicurl',
            'email': 'badpublicurl@example.com',
            'first_name': 'Bad',
            'last_name': 'Url',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        }, follow=True)
        self.assertContains(resp, 'We Couldn&#39;t Build Your Verification Link')
        verification_state = self.client.session.get('verification_email_state')
        self.assertFalse(verification_state['last_attempt_ok'])
        self.assertEqual(verification_state['last_error_code'], 'public_base_url_invalid')

    @patch('core.utils.time.sleep', return_value=None)
    @patch('core.utils.get_connection')
    @patch('core.utils.django_send_mail')
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.gmail.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='smtp-user@example.com',
        EMAIL_HOST_PASSWORD='app-password',
        EMAIL_USE_TLS=True,
        EMAIL_USE_SSL=False,
        EMAIL_TIMEOUT=8,
        EMAIL_FALLBACK_PORT=465,
        EMAIL_FALLBACK_USE_SSL=True,
        EMAIL_FALLBACK_USE_TLS=False,
    )
    def test_registration_falls_back_to_ssl_transport_when_primary_transport_fails(self, mock_send_mail, mock_get_connection, _mock_sleep):
        class DummyConnection:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        mock_get_connection.side_effect = lambda backend, **kwargs: DummyConnection(**kwargs)

        def _send_with_transport(subject, message, from_email, recipients, fail_silently=False, connection=None):
            if connection.port == 587:
                raise SMTPServerDisconnected('connection lost')
            return 1

        mock_send_mail.side_effect = _send_with_transport

        resp = self.client.post(reverse('register_user'), {
            'username': 'fallbackverify',
            'email': 'fallbackverify@example.com',
            'first_name': 'Fallback',
            'last_name': 'Verify',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        }, follow=True)

        self.assertContains(resp, 'Check Your Email')
        self.assertEqual(mock_send_mail.call_count, 2)
        primary_kwargs = mock_get_connection.call_args_list[0].kwargs
        fallback_kwargs = mock_get_connection.call_args_list[1].kwargs
        self.assertEqual(primary_kwargs['port'], 587)
        self.assertTrue(primary_kwargs['use_tls'])
        self.assertFalse(primary_kwargs['use_ssl'])
        self.assertEqual(primary_kwargs['timeout'], 8)
        self.assertEqual(fallback_kwargs['port'], 465)
        self.assertFalse(fallback_kwargs['use_tls'])
        self.assertTrue(fallback_kwargs['use_ssl'])
        self.assertEqual(fallback_kwargs['timeout'], 8)

    def test_registration_does_not_auto_login(self):
        """After registration, user should NOT be logged in."""
        self.client.post(reverse('register_user'), {
            'username': 'verifyuser',
            'email': 'verify@example.com',
            'first_name': 'Verify',
            'last_name': 'User',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        # Trying to access dashboard should redirect to login
        dashboard_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dashboard_resp.status_code, 302)
        self.assertIn('/login/', dashboard_resp.url)

    def test_registration_creates_unverified_user(self):
        """Newly registered user should have email_verified=False."""
        self.client.post(reverse('register_user'), {
            'username': 'unverified',
            'email': 'unverified@example.com',
            'first_name': 'Un',
            'last_name': 'Verified',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        user = User.objects.get(username='unverified')
        self.assertFalse(user.email_verified)

    def test_unverified_user_cannot_login(self):
        """Unverified user should not be allowed to log in."""
        User.objects.create_user(
            username='noverify', email='noverify@example.com',
            password='C0mpl3xP@ss!', email_verified=False,
        )
        resp = self.client.post(reverse('login'), {
            'username': 'noverify',
            'password': 'C0mpl3xP@ss!',
        })
        # Should NOT redirect — stays on login page with warning
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get('email_unverified'))

    def test_verified_user_can_login(self):
        """Verified user should log in normally."""
        _create_user(username='verified', email='verified@example.com')
        resp = self.client.post(reverse('login'), {
            'username': 'verified',
            'password': 'Str0ngP@ss!',
        })
        self.assertEqual(resp.status_code, 302)

    def test_valid_verification_link(self):
        """Clicking a valid verification link should verify and log in the user."""
        user = User.objects.create_user(
            username='linkuser', email='link@example.com',
            password='C0mpl3xP@ss!', email_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        resp = self.client.get(reverse('verify_email', kwargs={
            'uidb64': uid, 'token': token,
        }))
        self.assertRedirects(resp, reverse('dashboard'))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_invalid_verification_link(self):
        """Invalid token should show error page."""
        user = User.objects.create_user(
            username='badtoken', email='badtoken@example.com',
            password='C0mpl3xP@ss!', email_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        resp = self.client.get(reverse('verify_email', kwargs={
            'uidb64': uid, 'token': 'invalid-token',
        }))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verification Failed')
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_used_verification_link_rejected(self):
        """Once used, the verification token should be invalidated."""
        user = User.objects.create_user(
            username='usedtoken', email='used@example.com',
            password='C0mpl3xP@ss!', email_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        # Use it once
        self.client.get(reverse('verify_email', kwargs={
            'uidb64': uid, 'token': token,
        }))
        self.client.logout()
        # Try to use it again — token is invalidated because user state changed
        resp = self.client.get(reverse('verify_email', kwargs={
            'uidb64': uid, 'token': token,
        }))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Verification Failed')

    def test_resend_verification_rejects_get(self):
        """GET to resend endpoint should redirect to login."""
        resp = self.client.get(reverse('resend_verification'))
        self.assertEqual(resp.status_code, 302)

    def test_resend_verification_after_registration_sends_new_email(self):
        self.client.post(reverse('register_user'), {
            'username': 'resenduser',
            'email': 'resend@example.com',
            'first_name': 'Re',
            'last_name': 'Send',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertEqual(len(mail.outbox), 1)
        resp = self.client.post(reverse('resend_verification'))
        self.assertRedirects(resp, reverse('verification_sent'))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[-1].to, ['resend@example.com'])
        verification_state = self.client.session.get('verification_email_state')
        self.assertTrue(verification_state['last_attempt_ok'])

    @patch('core.utils.time.sleep', return_value=None)
    @patch('core.utils.django_send_mail', side_effect=SMTPServerDisconnected('connection lost'))
    def test_resend_verification_failure_updates_delivery_state(self, _mock_send_mail, _mock_sleep):
        user = User.objects.create_user(
            username='resendfail',
            email='resendfail@example.com',
            password='C0mpl3xP@ss!',
            email_verified=False,
        )
        session = self.client.session
        session['unverified_user_pk'] = user.pk
        session['verification_email_state'] = {'email': user.email, 'last_attempt_ok': None, 'last_error_code': ''}
        session.save()

        resp = self.client.post(reverse('resend_verification'), follow=True)

        self.assertContains(resp, 'We Couldn&#39;t Reach Our Email Provider')
        self.assertContains(resp, 'resendfail@example.com')
        self.assertContains(resp, 'We could not reach the email provider right now. Please try again shortly.')
        self.assertEqual(_mock_send_mail.call_count, 1)
        verification_state = self.client.session.get('verification_email_state')
        self.assertFalse(verification_state['last_attempt_ok'])
        self.assertEqual(verification_state['last_error_code'], 'smtp_unavailable')

    @patch('core.utils.get_connection')
    @patch('core.utils.django_send_mail')
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.gmail.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='smtp-user@example.com',
        EMAIL_HOST_PASSWORD='app-password',
        EMAIL_USE_TLS=True,
        EMAIL_USE_SSL=False,
        EMAIL_TIMEOUT=30,
        VERIFICATION_EMAIL_TIMEOUT=8,
        VERIFICATION_EMAIL_MAX_ATTEMPTS=1,
        EMAIL_FALLBACK_PORT=465,
        EMAIL_FALLBACK_USE_SSL=True,
        EMAIL_FALLBACK_USE_TLS=False,
    )
    def test_resend_verification_uses_bounded_timeout_profile(self, mock_send_mail, mock_get_connection):
        class DummyConnection:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        mock_get_connection.side_effect = lambda backend, **kwargs: DummyConnection(**kwargs)

        def _send_with_transport(subject, message, from_email, recipients, fail_silently=False, connection=None):
            if connection.port == 587:
                raise SMTPServerDisconnected('connection lost')
            return 1

        mock_send_mail.side_effect = _send_with_transport

        user = User.objects.create_user(
            username='resendtimeout',
            email='resendtimeout@example.com',
            password='C0mpl3xP@ss!',
            email_verified=False,
        )
        session = self.client.session
        session['unverified_user_pk'] = user.pk
        session['verification_email_state'] = {'email': user.email, 'last_attempt_ok': None, 'last_error_code': ''}
        session.save()

        resp = self.client.post(reverse('resend_verification'), follow=True)

        self.assertContains(resp, 'Check Your Email')
        self.assertEqual(mock_send_mail.call_count, 2)
        primary_kwargs = mock_get_connection.call_args_list[0].kwargs
        fallback_kwargs = mock_get_connection.call_args_list[1].kwargs
        self.assertEqual(primary_kwargs['timeout'], 8)
        self.assertEqual(fallback_kwargs['timeout'], 8)

    @override_settings(
        DEFAULT_FROM_EMAIL='',
        EMAIL_HOST_USER='smtp-user@example.com',
    )
    def test_verification_email_falls_back_to_smtp_user_as_sender(self):
        self.client.post(reverse('register_user'), {
            'username': 'fromfallback',
            'email': 'fromfallback@example.com',
            'first_name': 'From',
            'last_name': 'Fallback',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertEqual(mail.outbox[-1].from_email, 'smtp-user@example.com')

    def test_company_registration_requires_verification(self):
        """Company registration should also redirect to verification_sent."""
        resp = self.client.post(reverse('register_company'), {
            'username': 'verifycorp',
            'email': 'verifycorp@example.com',
            'company_name': 'VerifyCorp',
            'password1': 'C0mpl3xP@ss!',
            'password2': 'C0mpl3xP@ss!',
        })
        self.assertRedirects(resp, reverse('verification_sent'))
        user = User.objects.get(username='verifycorp')
        self.assertFalse(user.email_verified)

    def test_admin_role_auto_verified(self):
        """Users with role='admin' should be auto-verified on save."""
        user = User.objects.create_user(
            username='adminrole', email='adminrole@example.com',
            password='C0mpl3xP@ss!', role='admin',
        )
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_verification_sent_page_loads(self):
        """The verification_sent page should return 200."""
        resp = self.client.get(reverse('verification_sent'))
        self.assertEqual(resp.status_code, 200)


# ──────────────────────────────────────────────────────────────
#  PASSWORD CHANGE TESTS
# ──────────────────────────────────────────────────────────────

class CheckEmailCommandTests(TestCase):

    @patch('core.management.commands.check_email.send_email_result', return_value=EmailDeliveryResult(ok=True))
    def test_check_email_command_reports_success(self, _mock_send):
        out = StringIO()
        call_command('check_email', '--recipient', 'healthcheck@example.com', stdout=out)
        self.assertIn('Email delivery check passed.', out.getvalue())

    @patch(
        'core.management.commands.check_email.send_email_result',
        return_value=EmailDeliveryResult(ok=False, error_code='smtp_unavailable', retryable=True),
    )
    def test_check_email_command_raises_on_failure(self, _mock_send):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command('check_email', '--recipient', 'healthcheck@example.com', stdout=out)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_change_password_page_loads(self):
        resp = self.client.get(reverse('change_password'))
        self.assertEqual(resp.status_code, 200)

    def test_change_password_success(self):
        resp = self.client.post(reverse('change_password'), {
            'old_password': 'Str0ngP@ss!',
            'new_password1': 'N3wStr0ng@Pass!',
            'new_password2': 'N3wStr0ng@Pass!',
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('N3wStr0ng@Pass!'))

    def test_change_password_wrong_old(self):
        resp = self.client.post(reverse('change_password'), {
            'old_password': 'WrongPassword!',
            'new_password1': 'N3wStr0ng@Pass!',
            'new_password2': 'N3wStr0ng@Pass!',
        })
        self.assertEqual(resp.status_code, 200)  # form re-rendered with errors
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Str0ngP@ss!'))  # unchanged

    def test_change_password_mismatch(self):
        resp = self.client.post(reverse('change_password'), {
            'old_password': 'Str0ngP@ss!',
            'new_password1': 'N3wStr0ng@Pass!',
            'new_password2': 'DifferentPass!',
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Str0ngP@ss!'))


# ──────────────────────────────────────────────────────────────
#  APPLICATION WITHDRAWAL TESTS
# ──────────────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ApplicationSubmissionEmailTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.company_user, self.profile = _create_company_user()
        self.cat = JobCategory.objects.create(name='Engineering', slug='engineering')
        self.job = Job.objects.create(
            company=self.profile,
            title='Backend Engineer',
            category=self.cat,
            description='Build APIs',
            location='Remote',
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_apply_job_forwards_resume_attachment(self):
        resume = SimpleUploadedFile(
            'resume.pdf',
            b'%PDF-1.4 test resume',
            content_type='application/pdf',
        )
        resp = self.client.post(reverse('apply_job', args=[self.job.pk]), {
            'resume': resume,
            'cover_letter': 'Please review my resume.',
        })

        self.assertEqual(resp.status_code, 302)
        self.assertTrue(JobApplication.objects.filter(job=self.job, applicant=self.user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['company@example.com'])

        attachment = mail.outbox[0].attachments[0]
        attachment_name = getattr(attachment, 'filename', attachment[0])
        attachment_content = getattr(attachment, 'content', attachment[1])
        attachment_type = getattr(attachment, 'mimetype', attachment[2])
        self.assertEqual(attachment_name, 'resume.pdf')
        self.assertEqual(attachment_type, 'application/pdf')
        self.assertIn(b'%PDF-1.4', attachment_content)


class WithdrawApplicationTests(TestCase):
    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.user = _create_user()
        self.company_user, self.profile = _create_company_user()
        self.cat = JobCategory.objects.create(name='TestCat', slug='testcat')
        self.job = Job.objects.create(
            company=self.profile, title='Dev', category=self.cat,
            description='desc', job_type='full_time', location='Remote',
            deadline=timezone.now().date() + timedelta(days=30),
        )
        from .models import JobApplication
        self.application = JobApplication.objects.create(
            job=self.job, applicant=self.user,
            resume=SimpleUploadedFile('resume.pdf', b'data', content_type='application/pdf'),
            status='pending',
        )
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_withdraw_pending_succeeds(self):
        resp = self.client.post(reverse('withdraw_application', args=[self.application.pk]))
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'withdrawn')

    def test_withdraw_creates_notification(self):
        from .models import Notification
        self.client.post(reverse('withdraw_application', args=[self.application.pk]))
        notif = Notification.objects.filter(
            recipient=self.company_user, title='Application Withdrawn'
        )
        self.assertTrue(notif.exists())

    def test_withdraw_non_pending_fails(self):
        self.application.status = 'reviewed'
        self.application.save()
        self.client.post(reverse('withdraw_application', args=[self.application.pk]))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'reviewed')  # unchanged

    def test_withdraw_rejects_get(self):
        resp = self.client.get(reverse('withdraw_application', args=[self.application.pk]))
        self.assertEqual(resp.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'pending')  # unchanged

    def test_withdraw_other_user_404(self):
        other = _create_user(username='other', email='other@test.com')
        self.client.login(username='other', password='Str0ngP@ss!')
        resp = self.client.post(reverse('withdraw_application', args=[self.application.pk]))
        self.assertEqual(resp.status_code, 404)


# ──────────────────────────────────────────────────────────────
#  COMPANY VIEW APPLICANT TESTS
# ──────────────────────────────────────────────────────────────

class CompanyViewApplicantTests(TestCase):
    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.user = _create_user()
        self.company_user, self.profile = _create_company_user()
        self.cat = JobCategory.objects.create(name='TestCat', slug='testcat')
        self.job = Job.objects.create(
            company=self.profile, title='Dev', category=self.cat,
            description='desc', job_type='full_time', location='Remote',
            deadline=timezone.now().date() + timedelta(days=30),
        )
        from .models import JobApplication
        JobApplication.objects.create(
            job=self.job, applicant=self.user,
            resume=SimpleUploadedFile('resume.pdf', b'data', content_type='application/pdf'),
        )
        self.client.login(username='companyuser', password='Str0ngP@ss!')

    def test_view_applicant_profile(self):
        resp = self.client.get(reverse('company_view_applicant', args=[self.user.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.user.username)

    def test_view_applicant_from_other_company_blocked(self):
        other_company_user, other_profile = _create_company_user(
            username='other_co', email='other_co@test.com'
        )
        other_profile.company_name = 'OtherCorp'
        other_profile.save()
        self.client.login(username='other_co', password='Str0ngP@ss!')
        resp = self.client.get(reverse('company_view_applicant', args=[self.user.pk]))
        self.assertEqual(resp.status_code, 302)  # redirected

    def test_regular_user_blocked(self):
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('company_view_applicant', args=[self.user.pk]))
        self.assertEqual(resp.status_code, 302)  # role check redirect


# ──────────────────────────────────────────────────────────────
#  ACCOUNT DEACTIVATION TESTS
# ──────────────────────────────────────────────────────────────

class DeactivateAccountTests(TestCase):
    def setUp(self):
        self.user = _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')

    def test_deactivate_page_loads(self):
        resp = self.client.get(reverse('deactivate_account'))
        self.assertEqual(resp.status_code, 200)

    def test_deactivate_with_correct_password(self):
        resp = self.client.post(reverse('deactivate_account'), {'password': 'Str0ngP@ss!'})
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_deactivate_with_wrong_password(self):
        resp = self.client.post(reverse('deactivate_account'), {'password': 'WrongPass!'})
        self.assertEqual(resp.status_code, 200)  # form re-rendered
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)  # unchanged

    def test_deactivated_user_cannot_login(self):
        self.client.post(reverse('deactivate_account'), {'password': 'Str0ngP@ss!'})
        self.client.logout()
        success = self.client.login(username='testuser', password='Str0ngP@ss!')
        self.assertFalse(success)


# ──────────────────────────────────────────────────────────────
#  CONTACT FORM TESTS
# ──────────────────────────────────────────────────────────────

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ContactFormTests(TestCase):

    def test_contact_page_loads(self):
        resp = self.client.get(reverse('contact'))
        self.assertEqual(resp.status_code, 200)

    def test_valid_contact_submission(self):
        resp = self.client.post(reverse('contact'), {
            'name': 'Alice',
            'email': 'alice@example.com',
            'subject': 'Support',
            'message': 'I need help with my account.',
        })
        self.assertEqual(resp.status_code, 302)  # redirect on success

    def test_invalid_email_rejected(self):
        resp = self.client.post(reverse('contact'), {
            'name': 'Alice',
            'email': 'not-an-email',
            'subject': 'Support',
            'message': 'I need help.',
        })
        self.assertEqual(resp.status_code, 200)  # form re-rendered

    def test_missing_fields_rejected(self):
        resp = self.client.post(reverse('contact'), {
            'name': '',
            'email': 'alice@example.com',
            'subject': '',
            'message': '',
        })
        self.assertEqual(resp.status_code, 200)  # form re-rendered


# ──────────────────────────────────────────────────────────────
#  FILE UPLOAD VALIDATION TESTS
# ──────────────────────────────────────────────────────────────

class NewsletterTests(TestCase):
    def test_subscribe_valid_email(self):
        resp = self.client.post(reverse('newsletter_subscribe'), {'email': 'valid@example.com'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.content)['success'])
        self.assertTrue(NewsletterSubscription.objects.filter(email='valid@example.com').exists())

    def test_subscribe_invalid_email(self):
        resp = self.client.post(reverse('newsletter_subscribe'), {'email': 'not-an-email'})
        self.assertEqual(resp.status_code, 200)  # Returns 200 with success=False
        data = json.loads(resp.content)
        self.assertFalse(data['success'])
        self.assertIn('valid email', data['message'])
        self.assertFalse(NewsletterSubscription.objects.filter(email='not-an-email').exists())

        self.assertFalse(NewsletterSubscription.objects.filter(email='not-an-email').exists())


class FileUploadValidationTests(TestCase):
    """Tests for validate_file_extension, validate_file_size, validate_content_type."""

    def test_valid_extension_accepted(self):
        from .utils import validate_file_extension
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('test.pdf', b'%PDF-fake', content_type='application/pdf')
        # Should not raise
        validate_file_extension(f)

    def test_invalid_extension_rejected(self):
        from .utils import validate_file_extension
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        f = SimpleUploadedFile('malware.exe', b'MZ\x90', content_type='application/octet-stream')
        with self.assertRaises(ValidationError):
            validate_file_extension(f)

    def test_file_size_oversize_rejected(self):
        from .utils import validate_file_size
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        # 6 MB file with .jpg extension should be rejected (limit: 5 MB)
        data = b'\xff\xd8\xff' + b'\x00' * (6 * 1024 * 1024)
        f = SimpleUploadedFile('big.jpg', data, content_type='image/jpeg')
        with self.assertRaises(ValidationError) as ctx:
            validate_file_size(f)
        self.assertIn('too large', str(ctx.exception).lower())

    def test_file_size_valid_accepted(self):
        from .utils import validate_file_size
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 1 KB file with .pdf extension should be fine
        f = SimpleUploadedFile('small.pdf', b'%PDF' + b'\x00' * 1000, content_type='application/pdf')
        # Should not raise
        validate_file_size(f)

    def test_video_size_larger_limit(self):
        from .utils import validate_file_size
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 10 MB .mp4 should be accepted (limit: 50 MB)
        data = b'\x00' * (10 * 1024 * 1024)
        f = SimpleUploadedFile('video.mp4', data, content_type='video/mp4')
        validate_file_size(f)

    def test_content_type_valid_png_accepted(self):
        from .utils import validate_content_type
        from django.core.files.uploadedfile import SimpleUploadedFile
        # Valid PNG magic bytes
        png_header = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8
        f = SimpleUploadedFile('image.png', png_header, content_type='image/png')
        # Should not raise
        validate_content_type(f)

    def test_content_type_fake_png_rejected(self):
        from .utils import validate_content_type
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        # File named .png but contains EXE magic bytes
        f = SimpleUploadedFile('fake.png', b'MZ\x90\x00' + b'\x00' * 12, content_type='image/png')
        with self.assertRaises(ValidationError) as ctx:
            validate_content_type(f)
        self.assertIn('does not match', str(ctx.exception).lower())

    def test_content_type_valid_pdf_accepted(self):
        from .utils import validate_content_type
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('doc.pdf', b'%PDF-1.7' + b'\x00' * 8, content_type='application/pdf')
        validate_content_type(f)

    def test_content_type_fake_pdf_rejected(self):
        from .utils import validate_content_type
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        f = SimpleUploadedFile('evil.pdf', b'<html>' + b'\x00' * 10, content_type='application/pdf')
        with self.assertRaises(ValidationError):
            validate_content_type(f)

    def test_content_type_skips_docx(self):
        from .utils import validate_content_type
        from django.core.files.uploadedfile import SimpleUploadedFile
        # .docx has complex container format — should be skipped (no raise)
        f = SimpleUploadedFile('doc.docx', b'PK\x03\x04' + b'\x00' * 12, content_type='application/vnd.openxmlformats')
        validate_content_type(f)



class SearchAndListingRegressionTests(TestCase):
    def setUp(self):
        self.company_user, self.profile = _create_company_user(username='orbitco', email='orbitco@example.com')
        self.profile.company_name = 'Orbit Labs'
        self.profile.save(update_fields=['company_name'])
        self.category = JobCategory.objects.create(name='Engineering', slug='engineering')
        self.open_job = Job.objects.create(
            company=self.profile,
            category=self.category,
            title='Backend Engineer',
            description='Python APIs and integrations',
            location='Remote',
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.expired_job = Job.objects.create(
            company=self.profile,
            category=self.category,
            title='Expired Engineer',
            description='Legacy maintenance',
            location='Delhi',
            deadline=timezone.now().date() - timedelta(days=1),
        )

    def test_job_list_search_matches_company_name(self):
        resp = self.client.get(reverse('job_list'), {'q': 'Orbit'})
        self.assertContains(resp, 'Backend Engineer')
        self.assertNotContains(resp, 'Expired Engineer')

    def test_search_suggestions_match_company_name(self):
        resp = self.client.get(reverse('search_suggestions'), {'q': 'Orbit'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        titles = {item['title'] for item in data['results']}
        self.assertIn('Backend Engineer', titles)
        self.assertNotIn('Expired Engineer', titles)

    def test_search_suggestions_keep_frontend_payload_keys(self):
        resp = self.client.get(reverse('search_suggestions'), {'q': 'Orbit'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('pk', data['results'][0])
        self.assertIn('company__company_name', data['results'][0])

    def test_home_counts_only_open_jobs(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Backend Engineer')
        self.assertNotContains(resp, 'Expired Engineer')
        self.assertEqual(resp.context['stats']['jobs'], 1)
        self.assertEqual(list(resp.context['categories'])[0].job_count, 1)

    def test_company_detail_hides_expired_jobs(self):
        resp = self.client.get(reverse('company_detail', args=[self.profile.pk]))
        self.assertContains(resp, 'Backend Engineer')
        self.assertNotContains(resp, 'Expired Engineer')


class ProfileUpdateRegressionTests(TestCase):
    def test_user_profile_rejects_duplicate_email(self):
        _create_user(username='otheruser', email='taken@example.com')
        _create_user()
        self.client.login(username='testuser', password='Str0ngP@ss!')
        resp = self.client.post(reverse('user_profile'), {
            'first_name': '',
            'last_name': '',
            'email': 'taken@example.com',
            'phone': '',
            'bio': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context['form'], 'email', 'An account with this email already exists.')

    def test_company_profile_rejects_duplicate_email(self):
        _create_user(username='takenuser', email='taken@example.com')
        _create_company_user()
        self.client.login(username='companyuser', password='Str0ngP@ss!')
        resp = self.client.post(reverse('company_profile'), {
            'first_name': '',
            'last_name': '',
            'email': 'taken@example.com',
            'phone': '',
            'bio': '',
            'company_name': 'TestCorp',
            'industry': '',
            'website': '',
            'description': '',
            'address': '',
            'city': '',
            'state': '',
            'country': 'India',
            'established_year': '',
            'employee_count': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context['user_form'], 'email', 'An account with this email already exists.')


class BaseTemplateRegressionTests(TestCase):
    def test_dashboard_templates_use_shared_dash_markup(self):
        template_root = Path(settings.BASE_DIR) / 'templates'
        legacy_markers = (
            'btn btn-primary-gradient',
            'btn btn-glass',
            'glass-card',
            'table-dark-custom',
            'd-flex justify-content-between align-items-center mb-4',
        )

        dashboard_templates = []
        for template_path in template_root.rglob('*.html'):
            content = template_path.read_text(encoding='utf-8')
            if "extends 'dashboard_base.html'" in content:
                dashboard_templates.append((template_path, content))

        self.assertTrue(dashboard_templates)
        for template_path, content in dashboard_templates:
            self.assertIn('dash-page-header', content, msg=str(template_path))
            for marker in legacy_markers:
                self.assertNotIn(marker, content, msg=f'{template_path} still contains {marker!r}')

    def test_company_dashboard_does_not_link_to_user_profile(self):
        _create_company_user()
        self.client.login(username='companyuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, reverse('company_profile'))
        self.assertNotContains(resp, reverse('user_profile'))

    def test_admin_dashboard_does_not_link_to_user_profile(self):
        _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, reverse('dashboard'))
        self.assertNotContains(resp, reverse('user_profile'))
        self.assertNotContains(resp, 'Admin Panel')

    def test_csp_allows_cloudinary_assets(self):
        resp = self.client.get(reverse('home'))
        self.assertIn('https://res.cloudinary.com', resp['Content-Security-Policy'])

    def test_base_template_does_not_render_placeholder_footer_links(self):
        resp = self.client.get(reverse('home'))
        self.assertNotContains(resp, 'href="#" class="text-secondary fs-5"')
        self.assertContains(resp, 'https://github.com/harshbhogayata/TalentOrbit')


class AdminReportTests(TestCase):
    def setUp(self):
        _create_admin()
        self.client.login(username='adminuser', password='Str0ngP@ss!')

    def test_admin_report_download_returns_csv(self):
        resp = self.client.get(reverse('admin_download_report'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="talentorbit-admin-report-', resp['Content-Disposition'])
        content = resp.content.decode('utf-8')
        self.assertIn('section,item,value,detail_1,detail_2', content)
        self.assertIn('summary,total_users', content)


class CreateSuperuserCommandTests(TestCase):
    def test_skips_without_bootstrap_env_vars(self):
        out = StringIO()
        with patch.dict('os.environ', {
            'SUPERUSER_USERNAME': '',
            'SUPERUSER_EMAIL': '',
            'SUPERUSER_PASSWORD': '',
        }, clear=False):
            call_command('createsu', stdout=out)
        self.assertIn('Skipping superuser creation', out.getvalue())
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_creates_superuser_when_env_vars_present(self):
        out = StringIO()
        with patch.dict('os.environ', {
            'SUPERUSER_USERNAME': 'bootstrap-admin',
            'SUPERUSER_EMAIL': 'bootstrap@example.com',
            'SUPERUSER_PASSWORD': 'Sup3rSafePass!234',
        }, clear=False):
            call_command('createsu', stdout=out)
        self.assertIn('Successfully created new superuser', out.getvalue())
        self.assertTrue(User.objects.filter(username='bootstrap-admin', is_superuser=True).exists())
