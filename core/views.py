"""
TalentOrbit Views
=================
Views for all three roles: Admin, Company, User.
Covers auth, dashboards, jobs, tenders, quizzes, videos, subscriptions.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.text import slugify
from django.db.models import Q, Count
from django.http import JsonResponse
from django.urls import reverse
from functools import wraps

from .models import (
    User, CompanyProfile, JobCategory, Job, JobApplication,
    Tender, TenderBid, SkillVideo, Quiz, QuizQuestion,
    QuizAttempt, Notification, Subscription, NewsletterSubscription,
    SavedJob,
)
from .forms import (
    UserRegistrationForm, CompanyRegistrationForm, CustomLoginForm,
    UserProfileForm, CompanyProfileForm, JobForm, JobApplicationForm,
    TenderForm, TenderBidForm, JobCategoryForm, SkillVideoForm,
    QuizForm, QuizQuestionForm, ChangePasswordForm,
    DeactivateAccountForm, ContactForm
)


# ──────────────────────────────────────────────────────────────
#  DECORATORS
# ──────────────────────────────────────────────────────────────

def role_required(role):
    """Decorator to restrict view access by user role."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                messages.error(request, "You don't have permission to access this page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    return role_required('admin')(view_func)


def company_required(view_func):
    return role_required('company')(view_func)


def user_required(view_func):
    return role_required('user')(view_func)


def get_open_jobs_queryset():
    """Public-facing jobs: active and not past their deadline."""
    today = timezone.localdate()
    return Job.objects.filter(is_active=True).filter(
        Q(deadline__isnull=True) | Q(deadline__gte=today)
    )


# ──────────────────────────────────────────────────────────────
#  PUBLIC VIEWS
# ──────────────────────────────────────────────────────────────

def home(request):
    """Landing page."""
    today = timezone.localdate()
    open_job_count_filter = Q(jobs__is_active=True) & (
        Q(jobs__deadline__isnull=True) | Q(jobs__deadline__gte=today)
    )
    featured_jobs = get_open_jobs_queryset().select_related('company', 'category')[:6]
    categories = JobCategory.objects.filter(is_active=True).annotate(
        job_count=Count('jobs', filter=open_job_count_filter)
    )[:8]
    companies = CompanyProfile.objects.filter(status='approved')[:6]
    stats = {
        'jobs': get_open_jobs_queryset().count(),
        'companies': CompanyProfile.objects.filter(status='approved').count(),
        'users': User.objects.filter(role='user').count(),
        'categories': JobCategory.objects.filter(is_active=True).count(),
    }
    return render(request, 'home.html', {
        'featured_jobs': featured_jobs,
        'categories': categories,
        'companies': companies,
        'stats': stats,
    })


def job_list(request):
    """Public job listing with search and filters."""
    jobs = get_open_jobs_queryset().select_related('company', 'category')
    categories = JobCategory.objects.filter(is_active=True)

    # Search (includes location)
    q = request.GET.get('q', '')
    if q:
        jobs = jobs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) |
            Q(skills__name__icontains=q) | Q(location__icontains=q) |
            Q(company__company_name__icontains=q)
        ).distinct()

    # Filter by category
    cat = request.GET.get('category', '')
    if cat:
        jobs = jobs.filter(category__slug=cat)

    # Filter by job type
    jtype = request.GET.get('type', '')
    if jtype:
        jobs = jobs.filter(job_type=jtype)

    # Filter by experience
    exp = request.GET.get('experience', '')
    if exp:
        jobs = jobs.filter(experience=exp)

    # Filter by salary
    min_salary = request.GET.get('min_salary')
    if min_salary:
        try:
            val = float(min_salary)
            # Filter logic: if job.salary_max >= val or job.salary_min >= val
            # Simplest: job.salary_min >= val
            jobs = jobs.filter(salary_min__gte=val)
        except ValueError:
            pass

    # Pagination
    paginator = Paginator(jobs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Build query string for pagination links (exclude page param)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    saved_ids = []
    if request.user.is_authenticated and request.user.role == 'user':
        saved_ids = list(SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True))

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'query': q,
        'selected_category': cat,
        'selected_type': jtype,
        'selected_experience': exp,
        'query_string': query_string,
        'saved_ids': saved_ids,
        'breadcrumbs': [{'title': 'Jobs'}],
    })


def job_detail(request, pk):
    """Job detail page."""
    job = get_object_or_404(Job, pk=pk)
    has_applied = False
    is_saved = False
    if request.user.is_authenticated and request.user.role == 'user':
        has_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
        is_saved = SavedJob.objects.filter(user=request.user, job=job).exists()
    related_jobs = get_open_jobs_queryset().filter(
        category=job.category
    ).exclude(pk=pk)[:4]
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
        'is_saved': is_saved,
        'related_jobs': related_jobs,
        'breadcrumbs': [
            {'title': 'Jobs', 'url': reverse('job_list')},
            {'title': job.title},
        ],
    })


def company_list(request):
    """Public listing of approved companies."""
    companies = CompanyProfile.objects.filter(status='approved').order_by('-created_at')
    q = request.GET.get('q', '')
    if q:
        companies = companies.filter(
            Q(company_name__icontains=q) | Q(industry__icontains=q)
        )
    paginator = Paginator(companies, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'companies/company_list.html', {
        'page_obj': page_obj,
        'query': q,
        'query_string': query_string,
        'breadcrumbs': [{'title': 'Companies'}],
    })


def company_detail(request, pk):
    """Company public profile."""
    company = get_object_or_404(CompanyProfile, pk=pk, status='approved')
    jobs = get_open_jobs_queryset().filter(company=company)
    return render(request, 'companies/company_detail.html', {
        'company': company,
        'jobs': jobs,
        'breadcrumbs': [
            {'title': 'Companies', 'url': reverse('company_list')},
            {'title': company.company_name},
        ],
    })


# ──────────────────────────────────────────────────────────────
#  AUTH VIEWS
# ──────────────────────────────────────────────────────────────

def register_user(request):
    """User registration with email verification."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from .utils import send_verification_email
            send_verification_email(request, user)
            return redirect('verification_sent')
    else:
        form = UserRegistrationForm()
    return render(request, 'auth/register_user.html', {'form': form})


def register_company(request):
    """Company registration with email verification."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            from .utils import send_verification_email
            send_verification_email(request, user)
            return redirect('verification_sent')
    else:
        form = CompanyRegistrationForm()
    return render(request, 'auth/register_company.html', {'form': form})


def login_view(request):
    """Login view for all roles."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email_verified:
                # Store user PK in session so resend view can find them
                request.session['unverified_user_pk'] = user.pk
                return render(request, 'auth/login.html', {
                    'form': form,
                    'email_unverified': True,
                })
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
    else:
        form = CustomLoginForm()
    return render(request, 'auth/login.html', {'form': form})


def verification_sent(request):
    """Show 'check your email' page after registration or unverified login."""
    return render(request, 'auth/verification_sent.html')


def verify_email(request, uidb64, token):
    """
    Handle email verification link clicks.
    Validates UID+token, marks user as verified, logs them in, redirects to dashboard.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        login(request, user, backend='core.backends.EmailOrUsernameBackend')
        messages.success(request, 'Email verified successfully! Welcome to TalentOrbit.')
        return redirect('dashboard')
    else:
        messages.error(request, 'This verification link is invalid or has expired.')
        return render(request, 'auth/verification_invalid.html')


def resend_verification(request):
    """
    Resend verification email. POST-only, rate-limited via middleware.
    Uses session-stored user PK from the login view.
    """
    if request.method != 'POST':
        return redirect('login')

    user_pk = request.session.get('unverified_user_pk')
    if not user_pk:
        messages.error(request, 'No pending verification found. Please log in first.')
        return redirect('login')

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        messages.error(request, 'Account not found.')
        return redirect('login')

    if user.email_verified:
        messages.info(request, 'Your email is already verified. You can log in.')
        return redirect('login')

    from .utils import send_verification_email
    send_verification_email(request, user)
    messages.success(request, 'Verification email resent. Please check your inbox.')
    return redirect('verification_sent')


def logout_view(request):
    """Logout."""
    if request.method != 'POST':
        return redirect('home')
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


# ──────────────────────────────────────────────────────────────
#  DASHBOARD (role-based redirect)
# ──────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Route to role-specific dashboard."""
    if request.user.role == 'admin':
        return admin_dashboard(request)
    elif request.user.role == 'company':
        return company_dashboard(request)
    else:
        return user_dashboard(request)


# ──────────────────────────────────────────────────────────────
#  ADMIN VIEWS
# ──────────────────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    """Admin dashboard with stats."""
    context = {
        'total_users': User.objects.filter(role='user').count(),
        'total_companies': CompanyProfile.objects.count(),
        'pending_companies': CompanyProfile.objects.filter(status='pending').count(),
        'total_jobs': Job.objects.count(),
        'total_categories': JobCategory.objects.count(),
        'total_videos': SkillVideo.objects.count(),
        'total_quizzes': Quiz.objects.count(),
        'recent_users': User.objects.filter(role='user').order_by('-date_joined')[:5],
        'pending_company_list': CompanyProfile.objects.filter(status='pending')[:5],
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def admin_manage_companies(request):
    """Admin: list all companies."""
    companies = CompanyProfile.objects.all().select_related('user')
    status_filter = request.GET.get('status', '')
    if status_filter:
        companies = companies.filter(status=status_filter)
    paginator = Paginator(companies, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'admin_panel/manage_companies.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'query_string': query_string,
    })


@admin_required
def admin_approve_company(request, pk):
    """Admin: approve a company."""
    if request.method != 'POST':
        return redirect('admin_manage_companies')
    company = get_object_or_404(CompanyProfile, pk=pk)
    company.status = 'approved'
    company.save()
    Notification.objects.create(
        recipient=company.user,
        title='Company Approved!',
        message=f'Your company "{company.company_name}" has been approved. You can now post jobs.',
        notif_type='system'
    )
    messages.success(request, f'Company "{company.company_name}" has been approved.')
    return redirect('admin_manage_companies')


@admin_required
def admin_reject_company(request, pk):
    """Admin: reject a company."""
    if request.method != 'POST':
        return redirect('admin_manage_companies')
    company = get_object_or_404(CompanyProfile, pk=pk)
    company.status = 'rejected'
    company.save()
    Notification.objects.create(
        recipient=company.user,
        title='Company Registration Rejected',
        message=f'Your company "{company.company_name}" has been rejected. Please contact support.',
        notif_type='system'
    )
    messages.warning(request, f'Company "{company.company_name}" has been rejected.')
    return redirect('admin_manage_companies')


@admin_required
def admin_delete_company(request, pk):
    """Admin: delete a company and its user."""
    if request.method != 'POST':
        return redirect('admin_manage_companies')
    company = get_object_or_404(CompanyProfile, pk=pk)
    user = company.user
    company_name = company.company_name
    company.delete()
    user.delete()
    messages.success(request, f'Company "{company_name}" and its user account deleted.')
    return redirect('admin_manage_companies')


@admin_required
def admin_manage_users(request):
    """Admin: list all regular users."""
    users = User.objects.filter(role='user').order_by('-date_joined')
    paginator = Paginator(users, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/manage_users.html', {'page_obj': page_obj})


@admin_required
def admin_delete_user(request, pk):
    """Admin: delete a user."""
    if request.method != 'POST':
        return redirect('admin_manage_users')
    user = get_object_or_404(User, pk=pk, role='user')
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" has been deleted.')
    return redirect('admin_manage_users')


@admin_required
def admin_manage_categories(request):
    """Admin: manage job categories."""
    categories = JobCategory.objects.annotate(job_count=Count('jobs'))
    if request.method == 'POST':
        form = JobCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('admin_manage_categories')
    else:
        form = JobCategoryForm()
    return render(request, 'admin_panel/manage_categories.html', {'categories': categories, 'form': form})


@admin_required
def admin_edit_category(request, pk):
    """Admin: edit a category."""
    cat = get_object_or_404(JobCategory, pk=pk)
    if request.method == 'POST':
        form = JobCategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{cat.name}" updated.')
            return redirect('admin_manage_categories')
    else:
        form = JobCategoryForm(instance=cat)
    return render(request, 'admin_panel/edit_category.html', {'form': form, 'category': cat})


@admin_required
def admin_delete_category(request, pk):
    """Admin: delete a category."""
    if request.method != 'POST':
        return redirect('admin_manage_categories')
    cat = get_object_or_404(JobCategory, pk=pk)
    cat.delete()
    messages.success(request, 'Category deleted.')
    return redirect('admin_manage_categories')


@admin_required
def admin_manage_videos(request):
    """Admin: manage skill videos."""
    videos = SkillVideo.objects.all().select_related('uploaded_by', 'category')
    if request.method == 'POST':
        form = SkillVideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploaded_by = request.user
            video.save()
            messages.success(request, 'Video uploaded successfully.')
            return redirect('admin_manage_videos')
    else:
        form = SkillVideoForm()
    paginator = Paginator(videos, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/manage_videos.html', {'videos': page_obj, 'page_obj': page_obj, 'form': form})


@admin_required
def admin_delete_video(request, pk):
    """Admin: delete a video."""
    if request.method != 'POST':
        return redirect('admin_manage_videos')
    video = get_object_or_404(SkillVideo, pk=pk)
    video.delete()
    messages.success(request, 'Video deleted.')
    return redirect('admin_manage_videos')


@admin_required
def admin_manage_quizzes(request):
    """Admin: manage quizzes."""
    quizzes = Quiz.objects.annotate(question_count=Count('questions'))
    paginator = Paginator(quizzes, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/manage_quizzes.html', {'quizzes': page_obj, 'page_obj': page_obj})


@admin_required
def admin_create_quiz(request):
    """Admin: create a new quiz."""
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save()
            messages.success(request, f'Quiz "{quiz.title}" created. Now add questions.')
            return redirect('admin_quiz_questions', pk=quiz.pk)
    else:
        form = QuizForm()
    return render(request, 'admin_panel/create_quiz.html', {'form': form})


@admin_required
def admin_quiz_questions(request, pk):
    """Admin: add questions to a quiz."""
    quiz = get_object_or_404(Quiz, pk=pk)
    questions = quiz.questions.all()
    if request.method == 'POST':
        form = QuizQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            messages.success(request, 'Question added.')
            return redirect('admin_quiz_questions', pk=pk)
    else:
        form = QuizQuestionForm()
    return render(request, 'admin_panel/quiz_questions.html', {'quiz': quiz, 'questions': questions, 'form': form})


@admin_required
def admin_edit_question(request, pk):
    """Admin: edit a quiz question."""
    question = get_object_or_404(QuizQuestion, pk=pk)
    if request.method == 'POST':
        form = QuizQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question updated.')
            return redirect('admin_quiz_questions', pk=question.quiz.pk)
    else:
        form = QuizQuestionForm(instance=question)
    return render(request, 'admin_panel/edit_question.html', {
        'form': form, 'question': question, 'quiz': question.quiz,
    })


@admin_required
def admin_delete_question(request, pk):
    """Admin: delete a quiz question."""
    if request.method != 'POST':
        return redirect('admin_manage_quizzes')
    question = get_object_or_404(QuizQuestion, pk=pk)
    quiz_pk = question.quiz.pk
    question.delete()
    messages.success(request, 'Question deleted.')
    return redirect('admin_quiz_questions', pk=quiz_pk)


@admin_required
def admin_delete_quiz(request, pk):
    """Admin: delete a quiz."""
    if request.method != 'POST':
        return redirect('admin_manage_quizzes')
    quiz = get_object_or_404(Quiz, pk=pk)
    quiz.delete()
    messages.success(request, 'Quiz deleted.')
    return redirect('admin_manage_quizzes')


@admin_required
def admin_send_subscription_notification(request):
    """Admin: notify users whose subscription is about to expire."""
    if request.method != 'POST':
        return redirect('admin_dashboard')
    threshold = timezone.now() + timedelta(days=3)
    expiring_users = User.objects.filter(
        is_subscribed=True,
        subscription_expiry__lte=threshold,
        subscription_expiry__gte=timezone.now()
    )
    count = 0
    for user in expiring_users:
        Notification.objects.create(
            recipient=user,
            title='Subscription Expiring Soon',
            message=f'Your subscription expires on {user.subscription_expiry.strftime("%b %d, %Y")}. Renew now to keep access.',
            notif_type='subscription'
        )
        count += 1
    messages.success(request, f'Notifications sent to {count} users.')
    return redirect('admin_dashboard')


@admin_required
def admin_quiz_attempts(request, pk):
    """Admin: view attempts for a specific quiz."""
    quiz = get_object_or_404(Quiz, pk=pk)
    attempts = quiz.attempts.all().select_related('user').order_by('-completed_at')
    paginator = Paginator(attempts, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/quiz_attempts.html', {'quiz': quiz, 'page_obj': page_obj})


# ──────────────────────────────────────────────────────────────
#  COMPANY VIEWS
# ──────────────────────────────────────────────────────────────

@company_required
def company_dashboard(request):
    """Company dashboard."""
    try:
        profile = request.user.company_profile
    except CompanyProfile.DoesNotExist:
        messages.error(request, "Company profile not found. Please contact support.")
        return redirect('home')
    context = {
        'profile': profile,
        'total_jobs': profile.jobs.count(),
        'active_jobs': profile.jobs.filter(is_active=True).count(),
        'total_applications': JobApplication.objects.filter(job__company=profile).count(),
        'pending_applications': JobApplication.objects.filter(job__company=profile, status='pending').count(),
        'total_tenders': profile.posted_tenders.count(),
        'recent_applications': JobApplication.objects.filter(job__company=profile).select_related('applicant', 'job').order_by('-applied_at')[:5],
    }
    return render(request, 'company/dashboard.html', context)


@company_required
def company_profile(request):
    """Company profile edit."""
    profile = request.user.company_profile
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        profile_form = CompanyProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('company_profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = CompanyProfileForm(instance=profile)
    return render(request, 'company/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    })


@company_required
def company_post_job(request):
    """Company posts a new job."""
    profile = request.user.company_profile
    if profile.status != 'approved':
        messages.warning(request, 'Your company needs admin approval before posting jobs.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.company = profile

            # Auto-create category if new
            new_cat_name = form.cleaned_data.get('new_category', '').strip()
            if new_cat_name and not job.category:
                cat, created = JobCategory.objects.get_or_create(
                    name=new_cat_name,
                    defaults={'slug': slugify(new_cat_name)}
                )
                job.category = cat

            job.save()
            # Save skills via the form's M2M logic (must call after job.save())
            form.save_m2m_skills(job)
            messages.success(request, f'Job "{job.title}" posted successfully!')
            return redirect('company_manage_jobs')
    else:
        form = JobForm()
    return render(request, 'company/post_job.html', {'form': form})


@company_required
def company_manage_jobs(request):
    """Company views and manages their jobs."""
    profile = request.user.company_profile
    jobs = profile.jobs.all().annotate(app_count=Count('applications'))
    return render(request, 'company/manage_jobs.html', {'jobs': jobs})


@company_required
def company_edit_job(request, pk):
    """Edit a job posting."""
    job = get_object_or_404(Job, pk=pk, company=request.user.company_profile)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            # Fix: Save M2M skills
            form.save_m2m_skills(job)
            messages.success(request, 'Job updated.')
            return redirect('company_manage_jobs')
    else:
        form = JobForm(instance=job)
    return render(request, 'company/edit_job.html', {'form': form, 'job': job})


@company_required
def company_delete_job(request, pk):
    """Delete a job posting."""
    if request.method != 'POST':
        return redirect('company_manage_jobs')
    job = get_object_or_404(Job, pk=pk, company=request.user.company_profile)
    job.delete()
    messages.success(request, 'Job deleted.')
    return redirect('company_manage_jobs')


@company_required
def company_toggle_job(request, pk):
    """Toggle job active status."""
    if request.method != 'POST':
        return redirect('company_manage_jobs')
    job = get_object_or_404(Job, pk=pk, company=request.user.company_profile)
    job.is_active = not job.is_active
    job.save()
    status = 'activated' if job.is_active else 'deactivated'
    messages.success(request, f'Job {status}.')
    return redirect('company_manage_jobs')


@company_required
def company_view_applications(request, job_pk):
    """View applications for a specific job."""
    job = get_object_or_404(Job, pk=job_pk, company=request.user.company_profile)
    applications = job.applications.all().select_related('applicant')
    return render(request, 'company/view_applications.html', {'job': job, 'applications': applications})


@company_required
def company_update_application(request, pk, status):
    """Update application status."""
    if request.method != 'POST':
        return redirect('company_manage_jobs')
    application = get_object_or_404(
        JobApplication, pk=pk, job__company=request.user.company_profile
    )
    if status in ['reviewed', 'shortlisted', 'rejected']:
        application.status = status
        application.save()
        Notification.objects.create(
            recipient=application.applicant,
            title=f'Application {status.title()}',
            message=f'Your application for "{application.job.title}" has been {status}.',
            notif_type='application'
        )
        messages.success(request, f'Application marked as {status}.')
    return redirect('company_view_applications', job_pk=application.job.pk)


@admin_required
def admin_manage_jobs(request):
    """Admin: manage all jobs."""
    jobs = Job.objects.all().select_related('company', 'category').order_by('-created_at')
    paginator = Paginator(jobs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/manage_jobs.html', {'page_obj': page_obj})


@admin_required
def admin_delete_job(request, pk):
    """Admin: delete a job."""
    if request.method != 'POST':
        return redirect('admin_manage_jobs')
    job = get_object_or_404(Job, pk=pk)
    title = job.title
    job.delete()
    messages.success(request, f'Job "{title}" deleted.')
    return redirect('admin_manage_jobs')


# ── TENDER VIEWS (Company) ──────────────────────────────────

@company_required
def company_tenders(request):
    """Company: view tenders (own + others)."""
    profile = request.user.company_profile
    my_tenders = Tender.objects.filter(posted_by=profile)
    other_tenders = Tender.objects.exclude(posted_by=profile).filter(status='open')
    return render(request, 'company/tenders.html', {
        'my_tenders': my_tenders,
        'other_tenders': other_tenders,
    })


@company_required
def company_create_tender(request):
    """Company: create a new tender."""
    if request.method == 'POST':
        form = TenderForm(request.POST)
        if form.is_valid():
            tender = form.save(commit=False)
            tender.posted_by = request.user.company_profile
            tender.save()
            messages.success(request, 'Tender created successfully.')
            return redirect('company_tenders')
    else:
        form = TenderForm()
    return render(request, 'company/create_tender.html', {'form': form})


@company_required
def company_tender_detail(request, pk):
    """View tender detail with bids."""
    tender = get_object_or_404(Tender, pk=pk)
    profile = request.user.company_profile
    is_owner = tender.posted_by == profile
    bids = tender.bids.all().select_related('bidder') if is_owner else None
    my_bid = TenderBid.objects.filter(tender=tender, bidder=profile).first() if not is_owner else None
    has_bid = my_bid is not None

    # Check if tender deadline has passed
    tender_expired = tender.deadline < timezone.now().date()
    can_bid = not is_owner and not has_bid and tender.status == 'open' and not tender_expired

    if request.method == 'POST' and can_bid:
        form = TenderBidForm(request.POST)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.tender = tender
            bid.bidder = profile
            bid.save()
            Notification.objects.create(
                recipient=tender.posted_by.user,
                title='New Tender Bid',
                message=f'{profile.company_name} has bid on your tender "{tender.title}".',
                notif_type='tender'
            )
            messages.success(request, 'Bid submitted!')
            return redirect('company_tender_detail', pk=pk)
    else:
        form = TenderBidForm() if can_bid else None

    return render(request, 'company/tender_detail.html', {
        'tender': tender, 'is_owner': is_owner,
        'bids': bids, 'my_bid': my_bid, 'form': form,
    })


@company_required
def company_accept_bid(request, pk):
    """Accept a tender bid."""
    if request.method != 'POST':
        return redirect('company_tenders')
    bid = get_object_or_404(TenderBid, pk=pk, tender__posted_by=request.user.company_profile)
    bid.is_accepted = True
    bid.save()
    bid.tender.status = 'awarded'
    bid.tender.save()
    # Reject all other bids on this tender
    TenderBid.objects.filter(tender=bid.tender).exclude(pk=bid.pk).update(is_accepted=False)
    for other_bid in TenderBid.objects.filter(tender=bid.tender).exclude(pk=bid.pk).select_related('bidder__user'):
        Notification.objects.create(
            recipient=other_bid.bidder.user,
            title='Tender Bid Not Selected',
            message=f'Another bid was selected for "{bid.tender.title}". Thank you for participating.',
            notif_type='tender'
        )
    Notification.objects.create(
        recipient=bid.bidder.user,
        title='Tender Bid Accepted!',
        message=f'Your bid on "{bid.tender.title}" has been accepted!',
        notif_type='tender'
    )
    messages.success(request, f'Bid by {bid.bidder.company_name} accepted!')
    return redirect('company_tender_detail', pk=bid.tender.pk)


# ──────────────────────────────────────────────────────────────
#  USER VIEWS
# ──────────────────────────────────────────────────────────────

@user_required
def user_dashboard(request):
    """User dashboard."""
    context = {
        'applications': request.user.applications.all().select_related('job', 'job__company')[:5],
        'total_applications': request.user.applications.count(),
        'quiz_attempts': request.user.quiz_attempts.all()[:5],
        'notifications': request.user.notifications.filter(is_read=False)[:5],
        'subscription_active': request.user.subscription_active,
    }
    return render(request, 'user/dashboard.html', context)


@user_required
def user_profile(request):
    """User profile edit."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'user/profile.html', {'form': form})


@user_required
def apply_job(request, pk):
    """User applies to a job."""
    job = get_object_or_404(Job, pk=pk, is_active=True)
    if job.is_expired:
        messages.error(request, 'This job has passed its deadline and is no longer accepting applications.')
        return redirect('job_detail', pk=pk)
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied to this job.')
        return redirect('job_detail', pk=pk)

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()

            # Send email notification to company (Async)
            from .utils import send_email_async
            send_email_async(
                subject=f'New Application: {job.title}',
                message=f'{request.user.get_full_name()} has applied for {job.title}.\n\nCover Letter:\n{application.cover_letter}',
                recipient_list=[job.company.user.email]
            )

            Notification.objects.create(
                recipient=job.company.user,
                title='New Job Application',
                message=f'{request.user.get_full_name()} applied for "{job.title}".',
                notif_type='application'
            )
            messages.success(request, 'Application submitted! Your resume has been sent to the company.')
            return redirect('job_detail', pk=pk)
    else:
        form = JobApplicationForm()
    return render(request, 'user/apply_job.html', {
        'form': form,
        'job': job,
    })


@user_required
def user_application_detail(request, pk):
    """View details of a specific application."""
    application = get_object_or_404(JobApplication, pk=pk, applicant=request.user)
    return render(request, 'user/application_detail.html', {'application': application})


@user_required
def user_applications(request):
    """User views their applications."""
    applications = request.user.applications.all().select_related('job', 'job__company')
    paginator = Paginator(applications, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'user/applications.html', {'page_obj': page_obj})


# ── SAVED JOBS ───────────────────────────────────────────────

@user_required
def toggle_save_job(request, pk):
    """Toggle bookmark on a job."""
    if request.method != 'POST':
        return redirect('job_detail', pk=pk)
    job = get_object_or_404(Job, pk=pk)
    saved, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    if not created:
        saved.delete()
        messages.info(request, 'Job removed from saved list.')
    else:
        messages.success(request, 'Job saved!')
    # Return to referring page or job detail
    return redirect(request.META.get('HTTP_REFERER', reverse('job_detail', args=[pk])))


@user_required
def saved_jobs(request):
    """List user's saved/bookmarked jobs."""
    saved = SavedJob.objects.filter(user=request.user).select_related('job', 'job__company', 'job__category')
    paginator = Paginator(saved, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'user/saved_jobs.html', {'page_obj': page_obj})


# ── SUBSCRIPTION ─────────────────────────────────────────────

@user_required
# Removed duplicate @user_required
def subscription_page(request):
    """View subscription plans."""
    return render(request, 'user/subscription.html', {
        'is_subscribed': request.user.subscription_active,
        'expiry': request.user.subscription_expiry,
    })


@user_required
def subscribe(request, plan):
    """Legacy compatibility endpoint for the Razorpay-based subscription flow."""
    messages.info(request, 'Please complete checkout on the subscription page to activate a plan.')
    return redirect('subscription_page')


# ── VIDEOS ───────────────────────────────────────────────────

@user_required
def video_list(request):
    """List skill videos (premium check)."""
    videos = SkillVideo.objects.all()
    return render(request, 'user/videos.html', {
        'videos': videos,
        'subscription_active': request.user.subscription_active,
    })


@user_required
def video_detail(request, pk):
    """Watch a video."""
    video = get_object_or_404(SkillVideo, pk=pk)
    if video.is_premium and not request.user.subscription_active:
        messages.warning(request, 'Subscribe to access premium videos.')
        return redirect('subscription_page')
    return render(request, 'user/video_detail.html', {'video': video})


# ── QUIZZES ──────────────────────────────────────────────────

@user_required
def quiz_list(request):
    """List available quizzes."""
    quizzes = list(Quiz.objects.filter(is_active=True).annotate(question_count=Count('questions')))
    
    # Get latest attempts and passed status
    user_attempts = QuizAttempt.objects.filter(user=request.user).order_by('completed_at')
    latest_map = {a.quiz_id: a for a in user_attempts}
    passed_ids = set(QuizAttempt.objects.filter(user=request.user, passed=True).values_list('quiz_id', flat=True))

    for quiz in quizzes:
        quiz.latest_attempt = latest_map.get(quiz.pk)
        quiz.has_passed = quiz.pk in passed_ids

    return render(request, 'user/quiz_list.html', {'quizzes': quizzes})


@user_required
def take_quiz(request, pk):
    """Take a quiz."""
    quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
    questions = quiz.questions.all()
    total = questions.count()

    # Block quizzes with no questions
    if total == 0:
        messages.warning(request, 'This quiz has no questions yet.')
        return redirect('quiz_list')

    # Limit retakes to 3 per quiz
    attempt_count = QuizAttempt.objects.filter(user=request.user, quiz=quiz).count()
    if attempt_count >= 3:
        messages.warning(request, 'You have reached the maximum number of attempts (3) for this quiz.')
        return redirect('quiz_list')

    if request.method == 'POST':
        # Server-side time validation
        started_at = request.POST.get('started_at', '')
        if started_at:
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(started_at)
                elapsed_minutes = (timezone.now() - timezone.make_aware(start_time) if timezone.is_naive(start_time) else timezone.now() - start_time).total_seconds() / 60
                # Allow 1 extra minute for network latency
                if elapsed_minutes > quiz.time_limit + 1:
                    messages.error(request, 'Time limit exceeded. Your submission was not recorded.')
                    return redirect('quiz_list')
            except (ValueError, TypeError):
                pass

        score = 0
        for q in questions:
            answer = request.POST.get(f'question_{q.id}', '')
            if answer == q.correct_option:
                score += 1
        percentage = (score / total * 100) if total > 0 else 0
        passed = percentage >= quiz.passing_score

        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            total_questions=total,
            percentage=round(percentage, 1),
            passed=passed,
            completed_at=timezone.now(),
        )
        return render(request, 'user/quiz_result.html', {'attempt': attempt, 'quiz': quiz})

    return render(request, 'user/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'attempts_remaining': 3 - attempt_count,
    })


@user_required
def quiz_history(request):
    """User's quiz history."""
    attempts = QuizAttempt.objects.filter(user=request.user).select_related('quiz').order_by('-completed_at')
    paginator = Paginator(attempts, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'user/quiz_history.html', {'page_obj': page_obj})


# ── NOTIFICATIONS ────────────────────────────────────────────

@login_required
def notifications(request):
    """View all notifications."""
    notifs = request.user.notifications.all()
    paginator = Paginator(notifs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'notifications.html', {'notifications': page_obj, 'page_obj': page_obj})


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read."""
    if request.method != 'POST':
        return redirect('notifications')
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    return redirect('notifications')


@login_required
def mark_all_read(request):
    """Mark all notifications as read."""
    if request.method != 'POST':
        return redirect('notifications')
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications')


# ──────────────────────────────────────────────────────────────
#  SEARCH SUGGESTIONS API
# ──────────────────────────────────────────────────────────────

def search_suggestions(request):
    """JSON endpoint for job search autocomplete."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    jobs = get_open_jobs_queryset().filter(
        Q(title__icontains=q) |
        Q(skills__name__icontains=q) |
        Q(company__company_name__icontains=q)
    ).select_related('company').distinct().values(
        'pk', 'title', 'company__company_name', 'location'
    )[:8]
    return JsonResponse({'results': list(jobs)})


# ──────────────────────────────────────────────────────────────
#  STATIC PAGES
# ──────────────────────────────────────────────────────────────

def about(request):
    """About Us page."""
    stats = {
        'jobs': get_open_jobs_queryset().count(),
        'companies': CompanyProfile.objects.filter(status='approved').count(),
        'users': User.objects.filter(role='user').count(),
    }
    return render(request, 'pages/about.html', {'stats': stats})


def contact(request):
    """Contact Us page with validated form."""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                from django.conf import settings as django_settings
                send_mail(
                    subject=f'[TalentOrbit Contact] {cd["subject"]}',
                    message=f'From: {cd["name"]} <{cd["email"]}>\n\n{cd["message"]}',
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Contact form email failed: {e}")
            messages.success(request, 'Thank you for your message! We\'ll get back to you soon.')
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'pages/contact.html', {'form': form})


def privacy(request):
    """Privacy Policy page."""
    return render(request, 'pages/privacy.html')


def terms(request):
    """Terms of Service page."""
    return render(request, 'pages/terms.html')


# ──────────────────────────────────────────────────────────────
#  NEWSLETTER
# ──────────────────────────────────────────────────────────────

def newsletter_subscribe(request):
    """AJAX newsletter subscription."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'success': False, 'message': 'Please enter a valid email address.'})

            _, created = NewsletterSubscription.objects.get_or_create(email=email)
            if created:
                return JsonResponse({'success': True, 'message': 'Subscribed successfully!'})
            return JsonResponse({'success': True, 'message': 'You\'re already subscribed!'})
        return JsonResponse({'success': False, 'message': 'Please enter a valid email.'})
    return JsonResponse({'success': False}, status=405)



# ──────────────────────────────────────────────────────────────
#  CHANGE PASSWORD
# ──────────────────────────────────────────────────────────────

@login_required
def change_password(request):
    """In-app password change (no email reset required)."""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            if user.role == 'company':
                return redirect('company_profile')
            elif user.role == 'admin':
                return redirect('admin_dashboard')
            return redirect('user_profile')
    else:
        form = ChangePasswordForm(request.user)
    return render(request, 'user/change_password.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  APPLICATION WITHDRAWAL
# ──────────────────────────────────────────────────────────────

@user_required
def withdraw_application(request, pk):
    """Withdraw a pending job application. POST-only."""
    if request.method != 'POST':
        return redirect('user_applications')
    application = get_object_or_404(JobApplication, pk=pk, applicant=request.user)
    if application.status != 'pending':
        messages.error(request, 'Only pending applications can be withdrawn.')
        return redirect('user_applications')
    application.status = 'withdrawn'
    application.save(update_fields=['status'])
    Notification.objects.create(
        recipient=application.job.company.user,
        title='Application Withdrawn',
        message=f'{request.user.get_full_name() or request.user.username} withdrew their application for "{application.job.title}".',
        notif_type='application'
    )
    messages.success(request, f'Application for "{application.job.title}" withdrawn.')
    return redirect('user_applications')


# ──────────────────────────────────────────────────────────────
#  COMPANY VIEW APPLICANT PROFILE
# ──────────────────────────────────────────────────────────────

@company_required
def company_view_applicant(request, pk):
    """
    View an applicant's profile. Only accessible if the applicant has
    applied to at least one of this company's jobs.
    """
    applicant = get_object_or_404(User, pk=pk, role='user')
    company_profile = request.user.company_profile
    # Security: only allow viewing if applicant applied to this company
    has_applied = JobApplication.objects.filter(
        applicant=applicant, job__company=company_profile
    ).exists()
    if not has_applied:
        messages.error(request, 'You can only view profiles of applicants who applied to your jobs.')
        return redirect('company_manage_jobs')
    # Get all applications from this applicant to this company's jobs
    applications = JobApplication.objects.filter(
        applicant=applicant, job__company=company_profile
    ).select_related('job')
    return render(request, 'company/view_applicant.html', {
        'applicant': applicant,
        'applications': applications,
    })


# ──────────────────────────────────────────────────────────────
#  ACCOUNT DEACTIVATION
# ──────────────────────────────────────────────────────────────

@login_required
def deactivate_account(request):
    """Deactivate account (soft delete). Requires password confirmation."""
    if request.method == 'POST':
        form = DeactivateAccountForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.is_active = False
            user.save(update_fields=['is_active'])
            logout(request)
            messages.info(request, 'Your account has been deactivated. Contact support if you wish to reactivate.')
            return redirect('home')
    else:
        form = DeactivateAccountForm(request.user)
    return render(request, 'user/deactivate.html', {'form': form})


# ──────────────────────────────────────────────────────────────
#  ERROR HANDLERS
# ──────────────────────────────────────────────────────────────

def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)


# ──────────────────────────────────────────────────────────────
#  RAZORPAY PAYMENT VIEWS
# ──────────────────────────────────────────────────────────────

SUBSCRIPTION_PLANS = {
    'monthly':   {'amount': 299,  'days': 30,  'label': 'Monthly'},
    'quarterly': {'amount': 799,  'days': 90,  'label': 'Quarterly'},
    'yearly':    {'amount': 2499, 'days': 365, 'label': 'Yearly'},
}


@user_required
def create_razorpay_order(request, plan):
    """
    Create a Razorpay order and return order details as JSON.
    Called via AJAX from the subscription page before opening the payment modal.
    """
    try:
        import razorpay
    except ImportError:
        return JsonResponse({'error': 'Payment system not initialized (razorpay module missing).'}, status=500)

    from django.conf import settings as django_settings

    if plan not in SUBSCRIPTION_PLANS:
        return JsonResponse({'error': 'Invalid plan.'}, status=400)

    p = SUBSCRIPTION_PLANS[plan]
    
    if not django_settings.RAZORPAY_KEY_ID or not django_settings.RAZORPAY_KEY_SECRET:
         return JsonResponse({'error': 'Payment gateway configuration missing.'}, status=500)

    client = razorpay.Client(
        auth=(django_settings.RAZORPAY_KEY_ID, django_settings.RAZORPAY_KEY_SECRET)
    )

    try:
        order = client.order.create({
            'amount': p['amount'] * 100,   # paise
            'currency': 'INR',
            'receipt': f'sub_{request.user.pk}_{plan}',
            'notes': {
                'user_id': str(request.user.pk),
                'plan': plan,
            }
        })
    except Exception as e:
        import logging as _logging
        logger = _logging.getLogger(__name__)
        logger.error(f'Razorpay order creation failed: {e}')
        return JsonResponse({'error': 'Payment service unavailable. Please try again later.'}, status=503)

    return JsonResponse({
        'order_id':   order['id'],
        'amount':     order['amount'],
        'currency':   order['currency'],
        'key_id':     django_settings.RAZORPAY_KEY_ID,
        'plan_label': p['label'],
        'plan':       plan,
        'user_name':  request.user.get_full_name() or request.user.username,
        'user_email': request.user.email,
    })


@user_required
def verify_razorpay_payment(request):
    """
    Verify Razorpay payment signature after successful payment.
    Activates the subscription if verification passes.
    """
    import razorpay
    import hmac, hashlib
    from django.conf import settings as django_settings

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    razorpay_order_id   = request.POST.get('razorpay_order_id', '')
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
    razorpay_signature  = request.POST.get('razorpay_signature', '')
    plan                = request.POST.get('plan', '')

    if plan not in SUBSCRIPTION_PLANS:
        return JsonResponse({'error': 'Invalid plan.'}, status=400)

    # Verify signature
    key_secret = django_settings.RAZORPAY_KEY_SECRET.encode()
    payload    = f'{razorpay_order_id}|{razorpay_payment_id}'.encode()
    expected   = hmac.new(key_secret, payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        return JsonResponse({'error': 'Payment verification failed. Contact support.'}, status=400)

    # Signature valid — activate subscription
    p = SUBSCRIPTION_PLANS[plan]
    if request.user.subscription_active and request.user.subscription_expiry:
        expiry = request.user.subscription_expiry + timedelta(days=p['days'])
    else:
        expiry = timezone.now() + timedelta(days=p['days'])

    Subscription.objects.filter(user=request.user, is_active=True).update(is_active=False)
    Subscription.objects.create(
        user=request.user,
        plan=plan,
        amount=p['amount'],
        expires_at=expiry,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
    )
    request.user.is_subscribed = True
    request.user.subscription_expiry = expiry
    request.user.save(update_fields=['is_subscribed', 'subscription_expiry'])

    Notification.objects.create(
        recipient=request.user,
        title='Subscription Activated!',
        message=f'Your {p["label"]} plan is active until {expiry.strftime("%b %d, %Y")}.',
        notif_type='subscription'
    )

    return JsonResponse({'success': True, 'redirect': reverse('subscription_page')})
