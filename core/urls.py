"""
TalentOrbit URL Configuration (core app)
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Public ───────────────────────────────────────────────
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('companies/', views.company_list, name='company_list'),
    path('companies/<int:pk>/', views.company_detail, name='company_detail'),

    # ── Auth ─────────────────────────────────────────────────
    path('register/', views.register_user, name='register_user'),
    path('register/company/', views.register_company, name='register_company'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Email Verification ──────────────────────────────────
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('verification-sent/', views.verification_sent, name='verification_sent'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # ── Dashboard ────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Admin Panel ──────────────────────────────────────────
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/companies/', views.admin_manage_companies, name='admin_manage_companies'),
    path('admin-panel/companies/<int:pk>/approve/', views.admin_approve_company, name='admin_approve_company'),
    path('admin-panel/companies/<int:pk>/reject/', views.admin_reject_company, name='admin_reject_company'),
    path('admin-panel/companies/<int:pk>/delete/', views.admin_delete_company, name='admin_delete_company'),
    path('admin-panel/users/', views.admin_manage_users, name='admin_manage_users'),
    path('admin-panel/users/<int:pk>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/jobs/', views.admin_manage_jobs, name='admin_manage_jobs'),
    path('admin-panel/jobs/<int:pk>/delete/', views.admin_delete_job, name='admin_delete_job'),
    path('admin-panel/categories/', views.admin_manage_categories, name='admin_manage_categories'),
    path('admin-panel/categories/<int:pk>/edit/', views.admin_edit_category, name='admin_edit_category'),
    path('admin-panel/categories/<int:pk>/delete/', views.admin_delete_category, name='admin_delete_category'),
    path('admin-panel/videos/', views.admin_manage_videos, name='admin_manage_videos'),
    path('admin-panel/videos/<int:pk>/delete/', views.admin_delete_video, name='admin_delete_video'),
    path('admin-panel/quizzes/', views.admin_manage_quizzes, name='admin_manage_quizzes'),
    path('admin-panel/quizzes/create/', views.admin_create_quiz, name='admin_create_quiz'),
    path('admin-panel/quizzes/<int:pk>/questions/', views.admin_quiz_questions, name='admin_quiz_questions'),
    path('admin-panel/quizzes/questions/<int:pk>/edit/', views.admin_edit_question, name='admin_edit_question'),
    path('admin-panel/quizzes/questions/<int:pk>/delete/', views.admin_delete_question, name='admin_delete_question'),
    path('admin-panel/quizzes/<int:pk>/delete/', views.admin_delete_quiz, name='admin_delete_quiz'),
    path('admin-panel/quizzes/<int:pk>/attempts/', views.admin_quiz_attempts, name='admin_quiz_attempts'),
    path('admin-panel/send-notifications/', views.admin_send_subscription_notification, name='admin_send_notifications'),

    # ── Company ──────────────────────────────────────────────
    path('company/profile/', views.company_profile, name='company_profile'),
    path('company/jobs/post/', views.company_post_job, name='company_post_job'),
    path('company/jobs/', views.company_manage_jobs, name='company_manage_jobs'),
    path('company/jobs/<int:pk>/edit/', views.company_edit_job, name='company_edit_job'),
    path('company/jobs/<int:pk>/delete/', views.company_delete_job, name='company_delete_job'),
    path('company/jobs/<int:pk>/toggle/', views.company_toggle_job, name='company_toggle_job'),
    path('company/jobs/<int:job_pk>/applications/', views.company_view_applications, name='company_view_applications'),
    path('company/applications/<int:pk>/<str:status>/', views.company_update_application, name='company_update_application'),
    path('company/applicant/<int:pk>/', views.company_view_applicant, name='company_view_applicant'),
    path('company/tenders/', views.company_tenders, name='company_tenders'),
    path('company/tenders/create/', views.company_create_tender, name='company_create_tender'),
    path('company/tenders/<int:pk>/', views.company_tender_detail, name='company_tender_detail'),
    path('company/tenders/bids/<int:pk>/accept/', views.company_accept_bid, name='company_accept_bid'),

    # ── User ─────────────────────────────────────────────────
    path('user/profile/', views.user_profile, name='user_profile'),
    path('user/apply/<int:pk>/', views.apply_job, name='apply_job'),
    path('user/applications/', views.user_applications, name='user_applications'),
    path('user/applications/<int:pk>/', views.user_application_detail, name='user_application_detail'),
    path('user/saved-jobs/', views.saved_jobs, name='saved_jobs'),
    path('user/save-job/<int:pk>/', views.toggle_save_job, name='toggle_save_job'),
    path('user/subscription/', views.subscription_page, name='subscription_page'),
    path('user/subscribe/<str:plan>/', views.subscribe, name='subscribe'),
    path('user/payment/create-order/<str:plan>/', views.create_razorpay_order, name='create_razorpay_order'),
    path('user/payment/verify/', views.verify_razorpay_payment, name='verify_razorpay_payment'),
    path('user/videos/', views.video_list, name='video_list'),
    path('user/videos/<int:pk>/', views.video_detail, name='video_detail'),
    path('user/quizzes/', views.quiz_list, name='quiz_list'),
    path('user/quizzes/<int:pk>/', views.take_quiz, name='take_quiz'),
    path('user/quizzes/history/', views.quiz_history, name='quiz_history'),
    path('user/applications/<int:pk>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('user/password-change/', views.change_password, name='change_password'),
    path('user/deactivate/', views.deactivate_account, name='deactivate_account'),

    # ── Notifications ────────────────────────────────────────
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),

    # ── API ─────────────────────────────────────────────────
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),

    # ── Static Pages ────────────────────────────────────────
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),

    # ── Newsletter ──────────────────────────────────────────
    path('newsletter/', views.newsletter_subscribe, name='newsletter_subscribe'),
]
