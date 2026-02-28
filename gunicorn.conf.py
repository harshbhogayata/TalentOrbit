# =============================================================================
# Gunicorn Configuration — TalentOrbit
# =============================================================================

import multiprocessing

# Bind to all interfaces on port 8000
bind = "0.0.0.0:8000"

# Workers = 2 * CPU cores + 1  (safe default for most deployments)
workers = multiprocessing.cpu_count() * 2 + 1

# Use gthread worker class for handling concurrent requests
worker_class = "gthread"
threads = 2

# Timeout: allow 30s for requests (protects against slow clients)
timeout = 30
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"          # stdout
errorlog = "-"           # stderr
loglevel = "info"

# Security: limit request sizes
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Restart workers periodically to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50
