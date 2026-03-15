import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from smtplib import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPDataError,
    SMTPException,
    SMTPRecipientsRefused,
    SMTPResponseException,
    SMTPServerDisconnected,
)
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import DisallowedHost, ValidationError
from django.core.mail import send_mail as django_send_mail
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
NON_DELIVERING_EMAIL_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
}
RETRYABLE_EMAIL_ERROR_CODES = {
    'network_error',
    'smtp_data_error',
    'smtp_response_error',
    'smtp_unavailable',
    'zero_sent',
}

# Centralized allowed extensions - forms reference these to stay in sync
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx']
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.mov']

ALLOWED_EXTENSIONS_ALL = (
    ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS + ALLOWED_VIDEO_EXTENSIONS
)


@dataclass(frozen=True)
class EmailDeliveryResult:
    """Structured email delivery result for user-facing flows."""

    ok: bool
    error_code: str = ''
    retryable: bool = False

    def __bool__(self):
        return self.ok


EMAIL_DELIVERED = EmailDeliveryResult(ok=True)


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


# Size limits
MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5 MB
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024     # 50 MB


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


# Content-type sniffing (magic bytes)
# Maps extensions to the magic byte signatures they must start with.
_IMAGE_MAGIC = {
    '.jpg': [b'\xff\xd8\xff'],
    '.jpeg': [b'\xff\xd8\xff'],
    '.png': [b'\x89PNG'],
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
    except Exception as exc:
        raise ValidationError('Could not read the file. The upload may be corrupt.') from exc

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


def _classify_email_exception(exc):
    """Normalize SMTP and socket exceptions into stable error codes."""
    if isinstance(exc, SMTPAuthenticationError):
        return ('smtp_auth_failed', False)

    if isinstance(exc, SMTPRecipientsRefused):
        return ('recipient_rejected', False)

    if isinstance(exc, SMTPDataError):
        retryable = 400 <= getattr(exc, 'smtp_code', 0) < 500
        return ('smtp_data_error', retryable)

    if isinstance(exc, SMTPResponseException):
        retryable = 400 <= getattr(exc, 'smtp_code', 0) < 500
        return ('smtp_response_error', retryable)

    if isinstance(exc, (SMTPConnectError, SMTPServerDisconnected, TimeoutError, socket.timeout)):
        return ('smtp_unavailable', True)

    if isinstance(exc, OSError):
        return ('network_error', True)

    if isinstance(exc, SMTPException):
        return ('smtp_unavailable', True)

    return ('unexpected_email_error', True)


def _external_email_delivery_available(backend):
    return bool(backend) and backend not in NON_DELIVERING_EMAIL_BACKENDS


def _email_send_max_attempts():
    try:
        return max(1, int(getattr(settings, 'EMAIL_SEND_MAX_ATTEMPTS', 2)))
    except (TypeError, ValueError):
        return 2


def _email_retry_delay_seconds():
    try:
        return max(0.0, float(getattr(settings, 'EMAIL_RETRY_DELAY_SECONDS', 1.0)))
    except (TypeError, ValueError):
        return 1.0


def send_email_result(subject, message, recipient_list, from_email=None, require_external_delivery=False):
    """
    Send a single email and return a structured delivery result.
    """
    if from_email is None:
        from_email = get_default_from_email()

    recipients = [email.strip() for email in recipient_list if email and email.strip()]
    if not recipients:
        logger.warning('Email send skipped because no recipients were supplied. subject=%s', subject)
        return EmailDeliveryResult(ok=False, error_code='missing_recipient', retryable=False)

    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if require_external_delivery and not _external_email_delivery_available(backend):
        logger.error(
            'Email backend does not support external delivery. backend=%s subject=%s recipients=%s',
            backend,
            subject,
            recipients,
        )
        return EmailDeliveryResult(ok=False, error_code='email_backend_not_configured', retryable=False)

    if backend == 'django.core.mail.backends.console.EmailBackend':
        logger.warning(
            'Email backend is console-only; no real email will be delivered. '
            'subject=%s recipients=%s',
            subject,
            recipients,
        )

    max_attempts = _email_send_max_attempts() if require_external_delivery else 1
    retry_delay_seconds = _email_retry_delay_seconds()

    for attempt in range(1, max_attempts + 1):
        try:
            sent_count = django_send_mail(
                subject,
                message,
                from_email,
                recipients,
                fail_silently=False,
            )
        except Exception as exc:
            error_code, retryable = _classify_email_exception(exc)
            if (
                attempt < max_attempts
                and retryable
                and error_code in RETRYABLE_EMAIL_ERROR_CODES
            ):
                logger.warning(
                    'Transient email send failure; retrying. subject=%s from_email=%s '
                    'recipients=%s error_code=%s attempt=%s/%s',
                    subject,
                    from_email,
                    recipients,
                    error_code,
                    attempt,
                    max_attempts,
                )
                time.sleep(retry_delay_seconds * attempt)
                continue

            logger.exception(
                'Error sending email. subject=%s from_email=%s recipients=%s '
                'error_code=%s attempt=%s/%s',
                subject,
                from_email,
                recipients,
                error_code,
                attempt,
                max_attempts,
            )
            return EmailDeliveryResult(ok=False, error_code=error_code, retryable=retryable)

        if sent_count == 0:
            if attempt < max_attempts:
                logger.warning(
                    'Email send returned zero; retrying. subject=%s from_email=%s '
                    'recipients=%s attempt=%s/%s',
                    subject,
                    from_email,
                    recipients,
                    attempt,
                    max_attempts,
                )
                time.sleep(retry_delay_seconds * attempt)
                continue

            logger.warning(
                'Email send returned zero. subject=%s from_email=%s recipients=%s attempt=%s/%s',
                subject,
                from_email,
                recipients,
                attempt,
                max_attempts,
            )
            return EmailDeliveryResult(ok=False, error_code='zero_sent', retryable=True)

        return EMAIL_DELIVERED

    logger.error(
        'Email send exhausted retries without a terminal result. subject=%s recipients=%s',
        subject,
        recipients,
    )
    return EmailDeliveryResult(ok=False, error_code='smtp_unavailable', retryable=True)


def send_email(subject, message, recipient_list, from_email=None, require_external_delivery=False):
    """
    Send a single email and log failures instead of suppressing them.
    """
    return send_email_result(
        subject,
        message,
        recipient_list,
        from_email=from_email,
        require_external_delivery=require_external_delivery,
    ).ok


def send_email_async(subject, message, recipient_list, from_email=None, require_external_delivery=False):
    """
    Send email in a background thread for non-critical notifications.
    Test and local backends run inline to keep behavior deterministic.
    """
    backend = getattr(settings, 'EMAIL_BACKEND', '')
    if backend in INLINE_EMAIL_BACKENDS:
        return send_email(
            subject,
            message,
            recipient_list,
            from_email=from_email,
            require_external_delivery=require_external_delivery,
        )

    def _send():
        send_email(
            subject,
            message,
            recipient_list,
            from_email=from_email,
            require_external_delivery=require_external_delivery,
        )

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


def get_public_base_url(request=None):
    """
    Resolve the public application base URL.
    Prefer an explicit deployment URL when configured.
    """
    configured_base_url = getattr(settings, 'PUBLIC_APP_URL', '').strip()
    if configured_base_url:
        parsed_base_url = urlparse(configured_base_url)
        if parsed_base_url.scheme not in {'http', 'https'} or not parsed_base_url.netloc:
            logger.warning('Configured PUBLIC_APP_URL is invalid: %s', configured_base_url)
            raise ValueError('public_base_url_invalid')
        return configured_base_url.rstrip('/')

    if request is None:
        raise ValueError('public_base_url_unavailable')

    try:
        resolved_base_url = request.build_absolute_uri('/').rstrip('/')
    except DisallowedHost as exc:
        logger.exception('Unable to build an absolute URL for email links.')
        raise ValueError('public_base_url_invalid') from exc

    parsed_base_url = urlparse(resolved_base_url)
    if parsed_base_url.scheme not in {'http', 'https'} or not parsed_base_url.netloc:
        logger.warning('Resolved request host did not produce a valid public URL: %s', resolved_base_url)
        raise ValueError('public_base_url_invalid')
    return resolved_base_url


def make_verification_url(request, user):
    """
    Build an absolute email verification URL using Django's token generator.
    Uses the same UID+token pattern as password reset.
    Token validity is controlled by settings.PASSWORD_RESET_TIMEOUT.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    relative_url = reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    return urljoin(f'{get_public_base_url(request)}/', relative_url.lstrip('/'))


def send_verification_email(request, user):
    """
    Send a verification email to the given user.
    This is synchronous so registration/login flows can detect delivery issues.
    """
    recipient = (user.email or '').strip()
    if not recipient:
        logger.warning('Verification email skipped because user %s has no email address.', user.pk)
        return EmailDeliveryResult(ok=False, error_code='missing_recipient', retryable=False)

    try:
        verification_url = make_verification_url(request, user)
    except ValueError as exc:
        logger.warning(
            'Verification email skipped because the public URL could not be resolved. '
            'user=%s error_code=%s',
            user.pk,
            exc,
        )
        return EmailDeliveryResult(ok=False, error_code=str(exc), retryable=False)

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
    return send_email_result(
        subject,
        message,
        [recipient],
        require_external_delivery=True,
    )
