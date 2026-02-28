"""
Django Admin Registration for TalentOrbit models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, CompanyProfile, JobCategory, Job, JobApplication,
    Tender, TenderBid, SkillVideo, Quiz, QuizQuestion,
    QuizAttempt, Notification, Subscription
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'email_verified', 'is_subscribed', 'is_active')
    list_filter = ('role', 'email_verified', 'is_subscribed', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('TalentOrbit', {'fields': ('role', 'phone', 'bio', 'avatar', 'email_verified', 'is_subscribed', 'subscription_expiry')}),
    )


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'industry', 'status', 'created_at')
    list_filter = ('status', 'industry')
    search_fields = ('company_name', 'user__username')


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'category', 'job_type', 'is_active', 'created_at')
    list_filter = ('job_type', 'is_active', 'category')
    search_fields = ('title', 'company__company_name')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'job', 'status', 'applied_at')
    list_filter = ('status',)


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ('title', 'posted_by', 'status', 'deadline')
    list_filter = ('status',)


@admin.register(TenderBid)
class TenderBidAdmin(admin.ModelAdmin):
    list_display = ('tender', 'bidder', 'amount', 'is_accepted')


@admin.register(SkillVideo)
class SkillVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_premium', 'created_at')


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'time_limit', 'passing_score', 'is_active')
    inlines = [QuizQuestionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'percentage', 'passed')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'amount', 'is_active', 'expires_at')
