# Library Management System

> A production-ready, multi-tenant Django web application built with a domain-driven app structure, service layer, comprehensive tests, CSV/PDF import-export, and deployed on Vercel with Neon PostgreSQL.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-librarymsystem.vercel.app-black?style=flat-square&logo=vercel)](https://librarymsystem.vercel.app/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-008bb9?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech/)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

---

## Overview

A full-stack **multi-tenant** library management system where each admin owns an independent library instance — with their own books, students, issuances, and members. Built with a clean `apps/` domain structure, a dedicated service layer for business logic, and real test coverage across every app.

**[→ View Live Application](https://librarymsystem.vercel.app/)**

Deployed serverlessly on Vercel · Neon PostgreSQL backend · Cloudinary media storage · Google OAuth

sneak peek:
<img width="2519" height="1156" alt="image" src="https://github.com/user-attachments/assets/6c103cde-1ccd-485d-8171-f471e457042a" />
<img width="2488" height="1180" alt="image" src="https://github.com/user-attachments/assets/67f4a56f-f3c0-4f41-96cb-329d2669b2b1" />
<img width="2524" height="1178" alt="image" src="https://github.com/user-attachments/assets/a8201b4a-7431-4cfa-93a5-14f715e6bbe9" />
<img width="2499" height="1158" alt="image" src="https://github.com/user-attachments/assets/a58ff3c2-8e42-4d02-97c0-95aa7f9480ec" />




---

## Features

### Multi-Tenant Architecture
- Each admin creates and owns a `Library` instance with a unique auto-generated code
- All data (books, students, issuances) is fully scoped to the owning library
- `library_required` decorator enforces per-request library authorization on every view
- Admins can invite other users as members; invited users are prompted to change their temporary password on first login

### Book Management
- Full CRUD with inline bulk-editing and bulk deletion
- Search by title or author; filter by category (10 options) and language (English / Urdu)
- Inventory tracking with automatic low-stock alerts on the dashboard
- Paginated listings (10 per page)

### Student Management
- Student profiles with enrollment ID, name, phone, address, gender, and photo
- Search by name or enrollment number; filter by gender
- Bulk inline-edit and bulk delete

### Issuance & Returns
- Select2 searchable dropdowns for student and book selection
- Configurable return period (default: 15 days)
- Automatic PKR 500 fine calculation for overdue returns
- Status toggle — view all issued books or overdue-only
- Inline date editing; modal-confirmed returns
- `issue_book` / `return_book` service functions handle stock quantity atomically

### CSV & PDF Import / Export
- **Export CSV** — download complete book catalogue or student list as `.csv`
- **Export PDF** — paginated, styled PDF table via ReportLab (with landscape A4, alternating row colours)
- **Import CSV** — 3-step wizard: upload → column mapping UI → validated bulk create
  - Books: maps `name`, `author`, `quantity`, `category`, `language`; CSV data passed as base64 to survive HTML round-trips
  - Students: maps `name`, `enrollment`, `phone`, `address`, `gender`; duplicate enrollment detection before insert
  - Per-row error reporting; `transaction.atomic()` wraps all bulk inserts
- **Sample CSV download** — pre-filled template for both books and students

### Analytics Dashboard
- Summary cards — total books, issued count, overdue count, total members
- 6-month issuance and return trend (Chart.js line chart)
- Books status breakdown (doughnut: available / issued / overdue)
- Top-issued titles ranked by issue count
- Activity feed — latest 15 issuance events
- Low-stock alerts for books at or below threshold

### Authentication & Access Control
- Google OAuth via `django-allauth` — one-click sign-in
- Standard username/password registration and login with multi-library picker
- Force-password-change flow for newly invited members
- User profile — name, email, phone, date of birth, address, photo (Cloudinary)
- All dashboard routes protected by `library_required` (auth + library membership check)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2, Python 3.12 |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL via Neon (serverless) |
| Authentication | django-allauth 65.3 + Google OAuth2 |
| Frontend | Django Templates, custom CSS design system (Inter-based), Chart.js, Select2 |
| Filtering | django-filter 23.5 |
| PDF Export | ReportLab |
| Media Storage | Cloudinary (`django-cloudinary-storage`) |
| Static files | WhiteNoise 6.11 |
| Deployment | Vercel (serverless, Python 3.12 runtime) |
| WSGI | Gunicorn 21.2 |
| Image processing | Pillow 12.1 |

---

## Project Structure

```
Library-Management-System/
├── manage.py
├── requirements.txt
├── vercel.json                          # Vercel deployment config
├── build_files.sh                       # migrate + collectstatic for Vercel build
├── Procfile                             # Gunicorn process declaration
│
├── apps/                                # Domain-driven app layout
│   ├── core/                            # Library model, library_required decorator, dashboard
│   │   ├── models.py                    # Library, AdminProfile
│   │   ├── views.py                     # Dashboard, library context helpers
│   │   ├── services.py                  # create_library_with_owner
│   │   └── tests/test_models.py
│   ├── accounts/                        # Auth: login, signup, OAuth, multi-library picker
│   │   ├── views.py                     # AdminLoginView, signup, afterlogin
│   │   └── tests/test_models.py
│   ├── books/                           # Book and IssuedBook domain
│   │   ├── models.py                    # Book, IssuedBook
│   │   ├── views.py                     # CRUD + issuance views
│   │   ├── views_csv.py                 # CSV/PDF import-export
│   │   ├── services.py                  # issue_book, return_book
│   │   ├── filters.py                   # BookFilter
│   │   └── tests/test_models.py
│   ├── students/                        # Student domain
│   │   ├── models.py                    # StudentExtra
│   │   ├── views.py                     # CRUD views
│   │   ├── views_csv.py                 # CSV/PDF import-export
│   │   ├── filters.py                   # StudentFilter
│   │   └── tests/test_models.py
│   └── members/                         # Library membership & invitations
│       ├── models.py                    # LibraryMembership
│       ├── views.py                     # Manage members, invite flow
│       ├── services.py                  # add_member_to_library
│       └── tests/test_models.py
│
├── librarymanagement/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── library/                         # Legacy shell — preserves migration history only
│
├── static/
│   ├── vendor/                          # Third-party CSS/JS (Select2, Chart.js, etc.)
│   ├── metronic/assets/                 # Metronic 9 compiled CSS, JS, vendors

│
└── templates (inside each app's templates/)
    ├── library/                         # base.html, dashboard, books, issuance, profile
    └── student/                         # add/view student, CSV import
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- pip
- Git

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/noorrbutt/Library-Management-System-.git
cd Library-Management-System-

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # fill in values

# 5. Apply migrations
python manage.py migrate

# 6. Create a superuser (optional — or register via /adminsignup)
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

### Running Tests

```bash
python manage.py test apps
```

---

## Environment Variables

Create a `.env` file in the project root (never commit it) (There is a .env.example file provided as well):

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` in production |
| `DATABASE_URL` | PostgreSQL connection string; falls back to SQLite if unset |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name (for media storage) |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `EMAIL_HOST_USER` | Gmail address for system emails |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (not your account password) |

---

## Usage

1. **Sign in** via Google OAuth or admin credentials
2. **Create your library** on first login — you get a unique library code
3. **Invite members** from the Members panel — they receive a temporary password and must change it on first login
4. **Add books** — fill in title, author, quantity, category, language (or bulk-import via CSV)
5. **Register students** — enrollment ID, contact details, photo (or bulk-import via CSV)
6. **Issue books** — select student + book via searchable dropdowns, set return date
7. **Process returns** — click Return on any issued record, confirm in the modal
8. **Monitor** — dashboard shows trend charts, stock alerts, overdue counts, and recent activity

---

## Deployment

The project is configured for Vercel out of the box. The build command runs automatically:

```bash
# build_files.sh
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Set all environment variables in the Vercel dashboard before deploying. Media files are served via Cloudinary (no Vercel filesystem dependency).

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with a clear message: `git commit -m "feat: describe change"`
4. Push and open a Pull Request against `main`

---

## License

This project is licensed under the MIT License.

---

**Built by [Noor Butt](https://github.com/noorrbutt)**
