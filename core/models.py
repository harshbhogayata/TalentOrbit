"""
TalentOrbit Core Models
=======================
Custom User model with role-based access (Admin, Company, User),
plus all domain models: Company profiles, Jobs, Categories,
Tenders, Subscriptions, Videos, Quizzes, Resumes.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta


from .utils import validate_file_extension, validate_file_size, validate_content_type

class Skill(models.Model):
    """Normalized skills for better matching."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
        
    class Meta:
        ordering = ['name']

class User(AbstractUser):
    """Extended user with role support."""
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('company', 'Company'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, validators=[validate_file_extension, validate_file_size, validate_content_type])
    bio = models.TextField(blank=True)
    is_subscribed = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    subscription_expiry = models.DateTimeField(blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name='users')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    def save(self, *args, **kwargs):
        # Auto-verify admin users and superusers
        if self.role == 'admin' or self.is_superuser:
            self.email_verified = True
        super().save(*args, **kwargs)

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    @property
    def is_company_user(self):
        return self.role == 'company'

    @property
    def is_regular_user(self):
        return self.role == 'user'

    @property
    def subscription_active(self):
        if not self.is_subscribed:
            return False
        if self.subscription_expiry and self.subscription_expiry < timezone.now():
            # Auto-reset is_subscribed on expiry (write-through)
            self.is_subscribed = False
            self.save(update_fields=['is_subscribed'])
            return False
        return True


class CompanyProfile(models.Model):
    """Company profile linked to a User with role='company'."""
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, validators=[validate_file_extension, validate_file_size, validate_content_type])
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='India')
    established_year = models.PositiveIntegerField(blank=True, null=True)
    employee_count = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name_plural = "Company Profiles"


class JobCategory(models.Model):
    """Job categories managed by admin, auto-updated when companies add new ones."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Job Categories"
        ordering = ['name']


class Job(models.Model):
    """Job posting by a company."""
    JOB_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('remote', 'Remote'),
    )
    EXPERIENCE_CHOICES = (
        ('fresher', 'Fresher'),
        ('1-2', '1-2 Years'),
        ('3-5', '3-5 Years'),
        ('5-10', '5-10 Years'),
        ('10+', '10+ Years'),
    )
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=200)
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name='jobs')
    description = models.TextField()
    requirements = models.TextField(blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full_time')
    experience = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES, default='fresher')
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name='jobs')
    is_active = models.BooleanField(default=True)
    deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company.company_name}"

    class Meta:
        ordering = ['-created_at']

    @property
    def is_expired(self):
        if self.deadline:
            return self.deadline < timezone.now().date()
        return False

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f"₹{self.salary_min:,.0f} - ₹{self.salary_max:,.0f}"
        elif self.salary_min:
            return f"₹{self.salary_min:,.0f}+"
        return "Not Disclosed"


class JobApplication(models.Model):
    """User applies to a job; resume forwarded to company via email."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to='resumes/', validators=[validate_file_extension, validate_file_size, validate_content_type])
    cover_letter = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.applicant.username} → {self.job.title}"

    class Meta:
        unique_together = ['job', 'applicant']
        ordering = ['-applied_at']


class Tender(models.Model):
    """Tenders posted by companies, other companies can accept."""
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('awarded', 'Awarded'),
    )
    posted_by = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='posted_tenders')
    title = models.CharField(max_length=300)
    description = models.TextField()
    budget = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    deadline = models.DateField()
    requirements = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class TenderBid(models.Model):
    """Bid on a tender by another company."""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='tender_bids')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    proposal = models.TextField()
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid by {self.bidder.company_name} on {self.tender.title}"

    class Meta:
        unique_together = ['tender', 'bidder']


class SkillVideo(models.Model):
    """Videos uploaded by admin for subscribed users."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='skill_videos/', validators=[validate_file_extension, validate_file_size, validate_content_type])
    thumbnail = models.ImageField(upload_to='video_thumbnails/', blank=True, null=True, validators=[validate_file_extension, validate_file_size, validate_content_type])
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, blank=True)
    duration = models.CharField(max_length=20, blank=True, help_text="e.g., 15:30")
    is_premium = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_videos')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Quiz(models.Model):
    """Quiz created by admin."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, blank=True)
    time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
    passing_score = models.PositiveIntegerField(default=60, help_text="Passing percentage")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Quizzes"


class QuizQuestion(models.Model):
    """Individual question in a quiz."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=300)
    option_b = models.CharField(max_length=300)
    option_c = models.CharField(max_length=300)
    option_d = models.CharField(max_length=300)
    correct_option = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"

    class Meta:
        ordering = ['order']


class QuizAttempt(models.Model):
    """User's quiz attempt and score."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.percentage}%)"


class Notification(models.Model):
    """System notifications to users."""
    NOTIF_TYPES = (
        ('subscription', 'Subscription'),
        ('job', 'Job Update'),
        ('application', 'Application Status'),
        ('tender', 'Tender Update'),
        ('system', 'System'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=15, choices=NOTIF_TYPES, default='system')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.notif_type}] {self.title}"

    class Meta:
        ordering = ['-created_at']


class Subscription(models.Model):
    """Subscription plan and payments."""
    PLAN_CHOICES = (
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            durations = {
                'monthly': timedelta(days=30),
                'quarterly': timedelta(days=90),
                'yearly': timedelta(days=365),
            }
            self.expires_at = timezone.now() + durations.get(self.plan, timedelta(days=30))
        super().save(*args, **kwargs)


class SavedJob(models.Model):
    """User bookmarks a job for later."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'job']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} saved {self.job.title}"


class NewsletterSubscription(models.Model):
    """Newsletter email subscriptions."""
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email
