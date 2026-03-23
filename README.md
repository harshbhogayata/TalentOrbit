# TalentOrbit

TalentOrbit is a Django job marketplace focused on three roles:

- Job seekers who discover roles, apply with resumes, track applications, take quizzes, and unlock premium content with subscriptions.
- Companies that register for approval, manage profiles, post jobs, review applicants, and run tender workflows.
- Admins who moderate the platform, manage content, export reports, and oversee users and companies.

The project ships with server-rendered Django templates, a custom user model, email verification, payment support via Razorpay, optional Cloudinary media storage, and deployment configuration for both Docker and Render.

## Core Features

### Public platform

- Homepage with featured jobs, categories, companies, and platform stats
- Job search with category, type, experience, salary, and location filters
- Company directory and public company profiles
- Newsletter subscription endpoint
- Search suggestion API for job autocomplete

### Authentication and account flows

- Custom user model with `admin`, `company`, and `user` roles
- Login via username or email
- Email verification with resend flow
- Password reset and in-app password change
- Account deactivation flow

### Job seeker workspace

- Profile editing with avatar and skill tags
- Save jobs and manage bookmarks
- Apply to jobs with resume upload and cover letter
- Track application status and withdraw pending applications
- View premium videos and quizzes
- Purchase subscriptions through Razorpay
- Receive in-app notifications

### Company workspace

- Company registration and approval workflow
- Company profile management
- Create, edit, activate, and archive job listings
- Review applicants and update application status
- Create tenders, collect bids, and accept winning bids

### Admin workspace

- Admin dashboard and CSV report download
- Manage users, companies, jobs, categories, quizzes, and videos
- Create platform users and companies directly
- Send subscription notifications

### Operational and security features

- SQLite for local use, PostgreSQL-ready via `DATABASE_URL`
- WhiteNoise static serving
- Optional Cloudinary media storage with local fallback
- File extension, file size, and content-type validation
- In-memory rate limiting for auth/contact/newsletter endpoints
- Content Security Policy middleware
- Management commands for demo bootstrap, email checks, and subscription expiry cleanup
- Broad Django test coverage in `core/tests.py`

## Tech Stack

- Python 3.12
- Django 6
- Django REST Framework
- WhiteNoise
- Cloudinary
- Razorpay
- Gunicorn
- PostgreSQL or SQLite
- Docker / Docker Compose
- Render Blueprint deploy via `render.yaml`

## Project Structure

```text
TalentOrbit/
|-- core/                         # Models, views, forms, middleware, tests, management commands
|-- talentorbit/                  # Django project settings, URL config, ASGI/WSGI
|-- templates/                    # Public, admin, company, and user templates
|-- static/                       # CSS, JavaScript, icons
|-- nginx/                        # Nginx config for Docker deployment
|-- media/                        # Local media uploads in development (ignored by git)
|-- staticfiles/                  # Collected static output (ignored by git)
|-- docker-compose.yml            # Local container stack
|-- Dockerfile                    # Production-ready multi-stage image
|-- render.yaml                   # Render Blueprint deployment config
|-- requirements.txt              # Python dependencies
`-- .env.example                  # Environment variable template
```

## Local Setup

### 1. Create a virtual environment and install dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Create your environment file

Copy `.env.example` to `.env` and update the values for local development.

Minimum local changes:

- Set `SECRET_KEY` to a real Django secret
- Set `DEBUG=True`
- Set `ALLOWED_HOSTS=localhost,127.0.0.1`
- Set `PUBLIC_APP_URL=http://127.0.0.1:8000`
- Use `DATABASE_URL=sqlite:///db.sqlite3` unless you want PostgreSQL locally

Notes:

- If Cloudinary credentials are empty, uploads fall back to local `media/`
- If `EMAIL_URL` is not configured, Django falls back to a console-style email backend
- Razorpay is optional unless you need subscription checkout locally

### 3. Apply migrations

```powershell
python manage.py migrate
```

### 4. Optional: load demo data

Small hosted-style demo dataset:

```powershell
python manage.py bootstrap_demo --force
```

Larger development dataset:

```powershell
python manage.py seed_data
```

### 5. Run the development server

```powershell
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Demo Accounts

When `bootstrap_demo` is enabled, the command creates:

- `admin / demo1234`
- `techcorp / demo1234`
- `john_doe / demo1234`

## Useful Management Commands

```powershell
python manage.py test
python manage.py check_email --recipient you@example.com
python manage.py expire_subscriptions
python manage.py bootstrap_demo --force
python manage.py seed_data
```

Automatic superuser bootstrap is also available through:

```text
SUPERUSER_USERNAME
SUPERUSER_EMAIL
SUPERUSER_PASSWORD
```

and then:

```powershell
python manage.py createsu
```

## Docker

The repository includes:

- `Dockerfile` for a production-style multi-stage Python image
- `docker-compose.yml` for Django + PostgreSQL + Nginx

Start the container stack with:

```powershell
docker-compose up --build
```

Then run migrations inside the web container if needed:

```powershell
docker-compose exec web python manage.py migrate
```

## Deployment

### Render

The project already contains `render.yaml` for Blueprint deploys.

High-level flow:

1. Push the repository to GitHub.
2. Create a new Blueprint in Render.
3. Point it at this repository.
4. Set sensitive environment variables in the Render dashboard.

Important environment variables for production:

- `SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `PUBLIC_APP_URL`
- `EMAIL_URL`
- `DEFAULT_FROM_EMAIL`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `BOOTSTRAP_DEMO_DATA`
- `SUPERUSER_USERNAME`
- `SUPERUSER_EMAIL`
- `SUPERUSER_PASSWORD`

After deployment, verify SMTP configuration with:

```powershell
python manage.py check_email --recipient you@example.com
```

## Testing

The main regression suite lives in `core/tests.py` and covers:

- Models and permissions
- Registration, login, and email verification
- Password reset and password change
- Jobs, applications, saved jobs, and withdrawals
- Admin dashboards and reports
- Search and listing regressions
- Upload validation
- Demo bootstrap and email utility commands

Run the full suite with:

```powershell
python manage.py test
```

## Git Hygiene

The repository is configured to ignore local-only artifacts such as:

- `.env`
- SQLite databases
- uploaded media
- collected static files
- logs and temp files
- local editor and cache directories

Keep generated runtime assets out of version control and use `.env.example` as the committed configuration template.
