import logging
import os
import threading
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail as django_send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

INLINE_EMAIL_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
}

# Centralized allowed extensions — forms reference these to stay in sync
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']

ALLOWED_EXTENSIONS_ALL = (
    ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS + ALLOWED_VIDEO_EXTENSIONS
)


def validate_file_extension(value):
    """
    Model-level validator for uploaded files.
    Allows images, documents, and videos.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS_ALL:
        raise ValidationError(
            f'Unsupported file extension "{ext}". '
            f'Allowed: {", ".join(ALLOWED_EXTENSIONS_ALL)}'
        )


# ── Size limits ──────────────────────────────────────────────
MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5 MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024      # 50 MB


def _human_size(num_bytes):
    """Convert bytes to a human-readable string."""
    for unit in ('B', 'KB', 'MB'):
        if num_bytes < 1024:
            return f'{num_bytes:.1f} {unit}'
        num_bytes /= 1024
    return f'{num_bytes:.1f} GB'


def validate_file_size(value):
    """
    Enforce file-size limits based on extension type.
    Images/Documents: 5 MB, Videos: 50 MB.
    """
    ext = os.path.splitext(value.name)[1].lower()
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        limit = MAX_VIDEO_SIZE
    elif ext in ALLOWED_IMAGE_EXTENSIONS:
        limit = MAX_IMAGE_SIZE
    else:
        limit = MAX_DOCUMENT_SIZE

    if value.size > limit:
        raise ValidationError(
            f'File too large ({_human_size(value.size)}). '
            f'Maximum allowed: {_human_size(limit)}.'
        )


# ── Content-type sniffing (magic bytes) ──────────────────────
# Maps extensions to the magic byte signatures they must start with.
_IMAGE_MAGIC = {
    '.jpg':  [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.png':  [b'\x89PNG'],
    '.webp': [b'RIFF'],      # RIFF....WEBP
}

_PDF_MAGIC = [b'%PDF']


def validate_content_type(value):
    """
    Verify that the file's actual content matches its extension.
    Prevents disguised uploads (e.g. an .exe renamed to .jpg).
    Only checks file types with known magic byte signatures.
    """
    ext = os.path.splitext(value.name)[1].lower()

    signatures = None
    if ext in _IMAGE_MAGIC:
        signatures = _IMAGE_MAGIC[ext]
    elif ext == '.pdf':
        signatures = _PDF_MAGIC
    else:
        return  # skip check for .doc/.docx/.mp4 etc. (complex container formats)

    # Read the first 16 bytes (enough for all our checks)
    try:
        header = value.read(16)
        value.seek(0)   # rewind so Django can still save the file
    except Exception:
        raise ValidationError('Could not read the file. The upload may be corrupt.')

    if not any(header.startswith(sig) for sig in signatures):
        raise ValidationError(
            f'File content does not match its extension ("{ext}"). '
            f'The file may be corrupt or disguised.'
        )


def get_default_from_email():
    """
    Choose a sender address that matches the configured SMTP account when possible.
    """
    return (
        getattr(settings, 'DEFAULT_FROM_EMAIL', '').strip()
        or getattr(settings, 'EMAIL_HOST_USER', '').strip()
        or 'noreply@talentorbit.com'
    )


def send_email(subject, message, recipient_list, from_email=None):
    """
    Send a single email and log failures instead of suppressing them.
    """
    if from_email is None:
        from_email = get_default_from_email()

    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if backend == 'django.core.mail.backends.console.EmailBackend':
        logger.warning(
            'Email backend is console-only; no real email will be delivered. '
            'subject=%s recipients=%s',
            subject,
            recipient_list,
        )

    try:
        sent_count = django_send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'Error sending email. subject=%s from_email=%s recipients=%s',
            subject,
            from_email,
            recipient_list,
        )
        return False

    if sent_count == 0:
        logger.warning(
            'Email send returned zero. subject=%s from_email=%s recipients=%s',
            subject,
            from_email,
            recipient_list,
        )
        return False

    return True


def send_email_async(subject, message, recipient_list, from_email=None):
    """
    Send email in a background thread for non-critical notifications.
    Test and local backends run inline to keep behavior deterministic.
    """
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if backend in INLINE_EMAIL_BACKENDS:
        return send_email(subject, message, recipient_list, from_email=from_email)

    def _send():
        send_email(subject, message, recipient_list, from_email=from_email)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

def make_verification_url(request, user):
    """
    Build an absolute email verification URL using Django's token generator.
    Uses the same UID+token pattern as password reset.
    Token validity is controlled by settings.PASSWORD_RESET_TIMEOUT.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    relative_url = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    return request.build_absolute_uri(relative_url)


def send_verification_email(request, user):
    """
    Send a verification email to the given user.
    This is synchronous so registration/login flows can detect delivery issues.
    """
    verification_url = make_verification_url(request, user)
    subject = 'Verify your TalentOrbit email address'
    message = (
        f"Hi {user.get_full_name() or user.username},\n\n"
        f"Thanks for registering on TalentOrbit! Please verify your email address "
        f"by clicking the link below:\n\n"
        f"{verification_url}\n\n"
        f"This link will expire in 24 hours.\n\n"
        f"If you didn't create an account, you can safely ignore this email.\n\n"
        f"Thanks,\nTalentOrbit Team"
    )
    return send_email(subject, message, [user.email])
