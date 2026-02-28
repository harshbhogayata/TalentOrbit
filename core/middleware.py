"""
TalentOrbit Middleware
=====================
Rate limiting for auth/contact endpoints and Content-Security-Policy headers.
"""

import time
from collections import defaultdict
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin


# ──────────────────────────────────────────────────────────────
#  RATE LIMITING
# ──────────────────────────────────────────────────────────────

class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple in-memory IP-based rate limiter.
    Tracks request counts per IP per path-group within a sliding window.
    Returns 429 Too Many Requests when limits are exceeded.

    Limits:
      /login/, /register/, /register/company/  →  5 requests per 60 seconds
      /contact/, /newsletter/                  →  3 requests per 60 seconds
    """

    # {path_prefix: (max_requests, window_seconds)}
    RATE_LIMITS = {
        '/login/': (5, 60),
        '/register/': (5, 60),
        '/register/company/': (5, 60),
        '/contact/': (3, 60),
        '/newsletter/': (3, 60),
        '/resend-verification/': (3, 300),  # 3 resends per 5 minutes
    }

    # Storage: {(ip, path_prefix): [timestamp, timestamp, ...]}
    _requests = defaultdict(list)

    def _cleanup_old_requests(self):
        """Prevent unbounded memory growth by clearing if too large."""
        if len(self._requests) > 10000:
            self._requests.clear()

    def process_request(self, request):
        # Only rate-limit POST requests (form submissions)
        if request.method != 'POST':
            return None
        
        # Periodic cleanup check (simplistic but effective for this scale)
        if len(self._requests) > 10000:
            self._requests.clear()

        path = request.path
        matched_rule = None
        for prefix, limits in self.RATE_LIMITS.items():
            if path.startswith(prefix):
                matched_rule = (prefix, limits)
                break

        if not matched_rule:
            return None

        prefix, (max_requests, window) = matched_rule
        ip = self._get_client_ip(request)
        key = (ip, prefix)
        now = time.time()
        cutoff = now - window

        # Prune old entries
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= max_requests:
            retry_after = int(self._requests[key][0] + window - now) + 1
            return HttpResponse(
                self._rate_limit_response(retry_after),
                status=429,
                content_type='text/html',
                headers={'Retry-After': str(retry_after)},
            )

        self._requests[key].append(now)
        return None

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    @staticmethod
    def _rate_limit_response(retry_after):
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Too Many Requests</title>
<style>
body {{ font-family: 'Inter', sans-serif; background: #0a0a14; color: #e0e0e0;
       display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
.card {{ background: rgba(20,20,30,0.9); border: 1px solid rgba(255,255,255,0.08);
         border-radius: 16px; padding: 3rem; text-align: center; max-width: 450px; }}
h1 {{ color: #f87171; font-size: 1.5rem; }}
p {{ color: #94a3b8; }}
</style></head>
<body><div class="card">
<h1>429 — Too Many Requests</h1>
<p>You've made too many requests. Please try again in <strong>{retry_after}</strong> seconds.</p>
</div></body></html>"""


# ──────────────────────────────────────────────────────────────
#  CONTENT SECURITY POLICY
# ──────────────────────────────────────────────────────────────

class CSPMiddleware(MiddlewareMixin):
    """
    Injects a Content-Security-Policy header on every response.
    Allows only the specific CDNs TalentOrbit uses.
    """

    CSP_POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://checkout.razorpay.com",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",
        "img-src 'self' data: blob: https://*.razorpay.com",
        "media-src 'self'",
        "connect-src 'self' https://lumberjack.razorpay.com",
        "frame-src 'self' https://api.razorpay.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ])

    def process_response(self, request, response):
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.CSP_POLICY
        return response
