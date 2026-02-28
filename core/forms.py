"""
TalentOrbit Forms
=================
Registration, login, profile management, job posting,
tender management, and quiz forms.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, SetPasswordForm, PasswordResetForm
from django.utils import timezone
from .models import (
    User, CompanyProfile, Job, JobCategory, JobApplication,
    Tender, TenderBid, SkillVideo, Quiz, QuizQuestion, Subscription
)


# ──────────────────────────────────────────────────────────────
#  AUTH FORMS
# ──────────────────────────────────────────────────────────────

class UserRegistrationForm(UserCreationForm):
    """Registration form for regular users."""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Enter your email'
    }))
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'First Name'
    }))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Last Name'
    }))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Phone Number'
    }))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'user'
        if commit:
            user.save()
        return user


class CompanyRegistrationForm(UserCreationForm):
    """Registration form for companies."""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'Company Email'
    }))
    company_name = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Company Name'
    }))
    industry = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Industry (e.g., IT, Healthcare)'
    }))
    website = forms.URLField(required=False, widget=forms.URLInput(attrs={
        'class': 'form-control', 'placeholder': 'https://example.com'
    }))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control', 'rows': 3, 'placeholder': 'About your company'
    }))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'company'
        if commit:
            user.save()
            CompanyProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                industry=self.cleaned_data.get('industry', ''),
                website=self.cleaned_data.get('website', ''),
                description=self.cleaned_data.get('description', ''),
            )
        return user


class CustomLoginForm(AuthenticationForm):
    """Styled login form."""
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Username or Email', 'autofocus': True
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Password'
    }))


# ──────────────────────────────────────────────────────────────
#  PROFILE FORMS
# ──────────────────────────────────────────────────────────────

class UserProfileForm(forms.ModelForm):
    """Edit user profile."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio', 'avatar', 'skills']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'skills': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def clean_avatar(self):
        from .utils import ALLOWED_IMAGE_EXTENSIONS
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            if avatar.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image must be under 5MB.')
            ext = '.' + avatar.name.rsplit('.', 1)[-1].lower()
            allowed = ALLOWED_IMAGE_EXTENSIONS
            if ext not in allowed:
                raise forms.ValidationError(f'Only {", ".join(allowed)} images are allowed.')
        return avatar


class CompanyProfileForm(forms.ModelForm):
    """Edit company profile."""
    class Meta:
        model = CompanyProfile
        fields = [
            'company_name', 'industry', 'website', 'description',
            'logo', 'address', 'city', 'state', 'country',
            'established_year', 'employee_count'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'industry': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'established_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'employee_count': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 50-100'}),
        }

    def clean_logo(self):
        from .utils import ALLOWED_IMAGE_EXTENSIONS
        logo = self.cleaned_data.get('logo')
        if logo and hasattr(logo, 'size'):
            if logo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image must be under 5MB.')
            ext = '.' + logo.name.rsplit('.', 1)[-1].lower()
            allowed = ALLOWED_IMAGE_EXTENSIONS
            if ext not in allowed:
                raise forms.ValidationError(f'Only {", ".join(allowed)} images are allowed.')
        return logo


# ──────────────────────────────────────────────────────────────
#  JOB FORMS
# ──────────────────────────────────────────────────────────────

class JobForm(forms.ModelForm):
    """Create/edit a job posting."""
    new_category = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Or type a new category'}),
        help_text="If category not listed above, type a new one here"
    )

    class Meta:
        model = Job
        fields = [
            'title', 'category', 'description', 'requirements',
            'job_type', 'experience', 'salary_min', 'salary_max',
            'location', 'skills', 'deadline'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'experience': forms.Select(attrs={'class': 'form-select'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Salary'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Salary'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mumbai, India'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, React'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Python, Django, React'}),
        help_text="Comma-separated skills"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Pre-populate skills field from M2M
            self.fields['skills'].initial = ', '.join([s.name for s in self.instance.skills.all()])

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now().date():
            raise forms.ValidationError('Deadline cannot be in the past.')
        return deadline

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError('Minimum salary cannot be greater than maximum salary.')
        return cleaned_data

    def save_m2m_skills(self, job):
        """Save skills M2M relationship. Call after job.save()."""
        from django.utils.text import slugify
        from .models import Skill
        skill_names = [s.strip() for s in self.cleaned_data.get('skills', '').split(',') if s.strip()]
        new_skills = []
        for name in skill_names:
            slug = slugify(name)
            skill, _ = Skill.objects.get_or_create(slug=slug, defaults={'name': name})
            new_skills.append(skill)
        job.skills.set(new_skills)

    def save(self, commit=True):
        job = super().save(commit=False)
        if commit:
            job.save()
            self.save_m2m_skills(job)
        return job


class JobApplicationForm(forms.ModelForm):
    """Apply to a job with resume."""
    class Meta:
        model = JobApplication
        fields = ['resume', 'cover_letter']
        widgets = {
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Tell the employer why you\'re a great fit...'}),
        }

    def clean_resume(self):
        from .utils import ALLOWED_DOCUMENT_EXTENSIONS
        resume = self.cleaned_data.get('resume')
        if resume and hasattr(resume, 'size'):
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 5MB.')
            ext = '.' + resume.name.rsplit('.', 1)[-1].lower()
            allowed = ALLOWED_DOCUMENT_EXTENSIONS
            if ext not in allowed:
                raise forms.ValidationError(f'Only {", ".join(allowed)} files are allowed.')
        return resume


# ──────────────────────────────────────────────────────────────
#  TENDER FORMS
# ──────────────────────────────────────────────────────────────

class TenderForm(forms.ModelForm):
    """Create a tender."""
    class Meta:
        model = Tender
        fields = ['title', 'description', 'budget', 'deadline', 'requirements']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tender Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Estimated Budget'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now().date():
            raise forms.ValidationError('Deadline cannot be in the past.')
        return deadline


class TenderBidForm(forms.ModelForm):
    """Bid on a tender."""
    class Meta:
        model = TenderBid
        fields = ['amount', 'proposal']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Your Bid Amount'}),
            'proposal': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your proposal...'}),
        }


# ──────────────────────────────────────────────────────────────
#  ADMIN FORMS
# ──────────────────────────────────────────────────────────────

class JobCategoryForm(forms.ModelForm):
    """Admin form to manage job categories."""
    class Meta:
        model = JobCategory
        fields = ['name', 'slug', 'icon', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-briefcase'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SkillVideoForm(forms.ModelForm):
    """Admin uploads skill videos."""
    class Meta:
        model = SkillVideo
        fields = ['title', 'description', 'video_file', 'thumbnail', 'category', 'duration', 'is_premium']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'video_file': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15:30'}),
        }

    def clean_video_file(self):
        from .utils import ALLOWED_VIDEO_EXTENSIONS
        video = self.cleaned_data.get('video_file')
        if video and hasattr(video, 'size'):
            if video.size > 50 * 1024 * 1024:
                raise forms.ValidationError('Video must be under 50MB.')
            ext = '.' + video.name.rsplit('.', 1)[-1].lower()
            allowed = ALLOWED_VIDEO_EXTENSIONS
            if ext not in allowed:
                raise forms.ValidationError(f'Only {", ".join(allowed)} videos are allowed.')
        return video


class QuizForm(forms.ModelForm):
    """Admin creates a quiz."""
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'category', 'time_limit', 'passing_score', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class QuizQuestionForm(forms.ModelForm):
    """Admin adds a question to a quiz."""
    class Meta:
        model = QuizQuestion
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'order']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_option': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# ──────────────────────────────────────────────────────────────
#  CHANGE PASSWORD FORM
# ──────────────────────────────────────────────────────────────

class ChangePasswordForm(PasswordChangeForm):
    """Styled password change form with form-control widgets."""
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter current password'}),
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
    )


# ──────────────────────────────────────────────────────────────
#  DEACTIVATE ACCOUNT FORM
# ──────────────────────────────────────────────────────────────

class DeactivateAccountForm(forms.Form):
    """Requires password confirmation before deactivating account."""
    password = forms.CharField(
        label='Enter your password to confirm',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Your current password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('Incorrect password. Account deactivation cancelled.')
        return password


# ──────────────────────────────────────────────────────────────
#  PASSWORD RESET FORMS
# ──────────────────────────────────────────────────────────────

class StyledPasswordResetForm(PasswordResetForm):
    """Styled password reset request form (email input)."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'Enter your email address',
        }),
    )


class StyledSetPasswordForm(SetPasswordForm):
    """Styled new-password form used in the reset confirm step."""
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Enter new password',
        }),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Confirm new password',
        }),
    )


# ──────────────────────────────────────────────────────────────
#  CONTACT FORM
# ──────────────────────────────────────────────────────────────

class ContactForm(forms.Form):
    """Validated contact form with proper email checking."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Your name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'you@example.com',
        }),
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'How can we help?',
        }),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'placeholder': 'Tell us more...', 'rows': 5,
        }),
    )
