# 📚 Library Management System

A full-stack multi-tenant Django web application that lets independent libraries manage their books, members, issuances, returns, and real-time analytics, deployed on Vercel with a Neon PostgreSQL backend.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://librarymsystem.vercel.app/)
[![Django](https://img.shields.io/badge/Django-3.2-green.svg?logo=django)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10-blue.svg?logo=python)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-teal.svg?logo=postgresql)](https://neon.tech/)
[![UI](https://img.shields.io/badge/UI-Metronic%209%20Tailwind-blue.svg)](https://keenthemes.com/metronic)

## 🌐 Live Demo

**[View Live Application →](https://librarymsystem.vercel.app/)**

Deployed on Vercel with Neon PostgreSQL database and Google OAuth authentication.

---

## ✨ Features

### 🏛️ Multi-Tenant Architecture 
- **Isolated Libraries** — Each admin creates their own library instance; books, members, and records are fully scoped to that library
- **Defined Roles** — Only Owners of the respective library can add or remove members from their library. 
- **Google OAuth Routing** — First-time Google sign-in users are redirected to create a library; returning users land directly on their dashboard
- **Library Settings** — Only Owners i.e. Creators of the library can rename their library from the profile page
- **Zero Cross-Library Leakage** — Every ORM query is scoped by a `library` ForeignKey; URL manipulation cannot expose another library's data

  ### 📊 Analytics Dashboard
- **Real-time Statistics** — Total books, issued count, overdue count, total members — all scoped to the current library
- **Trend Charts** — 6-month line chart of issuance and return patterns (Chart.js)
- **Books Status** — Doughnut chart showing available vs issued vs overdue
- **Top Books** — Most frequently issued titles ranked by issue count
- **Activity Feed** — Latest 15 issuance events at a glance
- **Low Stock Alerts** — Books with quantity ≤ threshold flagged on dashboard

### 📖 Book Management
- **CRUD Operations** — Add, update, delete books with inline bulk editing and bulk deletion
- **Advanced Search & Filter** — Search by title, filter by category (10+ options) and language (English / Urdu)
- **Smart Inventory** — Stock tracking with automatic low-stock alerts on the dashboard
- **Pagination** — All book lists paginated for performance

### 👥 Member Management
- **Student Registration** — Complete profiles with name, enrollment ID, phone, address, gender, and photo
- **Search & Filter** — Quick lookup by name or enrollment number, filter by gender
- **Bulk Operations** — Inline edit and bulk delete multiple members simultaneously

### ↩️ Issuance & Returns
- **Smart Issuance** — Select2 dropdowns for student and book selection, filtered to current library only
- **Flexible Return Dates** — Default 15-day return period, customisable per record
- **Auto Fine Calculation** — PKR 500 penalty auto-calculated for overdue books
- **Status Tracking** — Toggle between all issued books and overdue-only view
- **Inline Editing** — Edit issue/return dates directly in the table; confirm returns with modal

### 👤 Authentication & Profiles
- **Google OAuth** — One-click sign-in via django-allauth, with automatic library routing
- **Admin Signup** — Creates user account and library in one step
- **Library-Scoped Login** — Multi-step login: select library → enter credentials → verified ownership
- **User Profile** — View and edit name, email, phone, date of birth, address, and profile photo
- **Role-based Access** — All dashboard routes protected.Only Owners of the library can add or remove members

### 🎨 UI
- **Metronic 9 Tailwind** — Clean, minimal admin dashboard theme
- **Shared base template** — Single `base.html` with persistent sidebar and top header showing library name and code
- **Responsive sidebar** — Mobile toggle, active link highlighting
- **Consistent components** — Unified cards, tables, badges, buttons, and form styling throughout

---

## 🏗️ Multi-Tenant Architecture

### Data Model

```
Library
  ├── name          (editable by admin)
  ├── code          (auto-generated, immutable — e.g. LIB-A3X9KZ)
  ├── owner         (ForeignKey → User)
  └── created_at

Book          → library (ForeignKey)
StudentExtra  → library (ForeignKey)
AdminProfile  → library (ForeignKey)
IssuedBook    → book → library (transitive)
```

### Data Isolation Guarantee

Every query that touches library-specific data follows this pattern:

```python
# All views use the @library_required decorator
@library_required
def viewbook_view(request):
    library = request.library        # injected by decorator
    books = Book.objects.filter(library=library)
```

Admin A can never see, modify, or delete Admin B's books, students, or records — even via direct URL manipulation.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 3.2.25, Python 3.10 |
| Database (Dev) | SQLite |
| Database (Prod) | PostgreSQL via Neon |
| Auth | django-allauth 0.54.0 + Google OAuth2 |
| Frontend | Django Templates, Metronic 9 Tailwind CSS, Chart.js, Bootstrap 5 (select pages) |
| Filtering | django-filter 23.5 |
| Static Files | WhiteNoise 6.11 |
| Deployment | Vercel |
| WSGI Server | Gunicorn 21.2 |
| Image Processing | Pillow 12.1 |

---

## 🗂️ Project Structure

```
Library-Management-System-/
├── manage.py
├── requirements.txt
├── vercel.json                   ← Vercel deployment config
├── build_files.sh                ← migrate + collectstatic for Vercel build
├── Procfile                      ← Gunicorn start command
├── test_multitenant.py           ← Multi-tenant isolation verification script
├── MULTITENANT_IMPLEMENTATION.md ← Detailed implementation notes
├── static/
│   ├── metronic/assets/          ← Metronic 9 compiled CSS, JS, favicon
│   │   ├── css/styles.css
│   │   ├── js/core.bundle.js
│   │   └── media/app/
│   ├── js/                       ← dashboard.js, userprofile.js
│   └── student/js/               ← viewbook.js, viewstudent.js, viewissuedbook.js
├── media/                        ← User-uploaded photos (dev only)
└── librarymanagement/
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── library/
        ├── models.py             ← Library, LibraryMembership, StudentExtra,
        │                            Book, IssuedBook, AdminProfile
        ├── views.py              ← All views; library_required decorator;
        │                            AdminLoginView; get_user_library helper
        ├── urls.py               ← App URL patterns
        ├── forms.py              ← ModelForms; AdminLoginForm; CreateLibraryForm
        ├── filters.py            ← BookFilter, StudentFilter (django-filter)
        ├── admin.py              ← Django admin registration
        ├── migrations/
        └── templates/
            ├── library/
            │   ├── base.html     ← Metronic shell; shows library name + code
            │   ├── dashboard.html
            │   ├── viewbook.html
            │   ├── addbook.html
            │   ├── issuebook.html
            │   ├── viewissuedbook.html
            │   ├── userprofile.html
            │   ├── adminlogin.html   ← Library selection grid
            │   ├── adminsignup.html
            │   ├── adminclick.html
            │   └── index.html        ← "Create" / "Login" CTAs
            └── student/
                ├── addstudent.html
                ├── viewstudent.html
                └── studentadded.html
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip
- Git

### 💻 Local Installation

```bash
# Clone the repository
git clone https://github.com/noorrbutt/Library-Management-System-.git
cd Library-Management-System-

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional — defaults to SQLite locally)
export DATABASE_URL=your_postgres_url
export GOOGLE_CLIENT_ID=your_client_id
export GOOGLE_CLIENT_SECRET=your_client_secret

# Apply database migrations
python manage.py migrate

# Run development server
python manage.py runserver
```
Open your browser at `http://127.0.0.1:8000/` and click **"Create Your Library"** to get started.

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string (falls back to SQLite if unset) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `DEBUG` | `True` for dev, `False` for production |
| `EMAIL_HOST_USER` | Gmail address for system emails |
| `EMAIL_HOST_PASSWORD` | Gmail App Password |

---

## 📖 Usage Guide

1. **Create a Library** — Go to the homepage and click "Create Your Library". Fill in your library name, username, email, and password. Your library is created instantly and you are logged in automatically.
2. **Login (returning users)** — Click "Log Into Existing Library", select your library from the grid, then enter your credentials.
3. **Add Books** — Fill in title, author, quantity, category, and language.
4. **Register Members** — Enter member info with a unique enrollment ID.
5. **Issue Books** — Select a member and a book via searchable dropdowns (only your library's data is shown), then set a return date.
6. **Process Returns** — Click Return on any issued record and confirm in the modal.
7. **Monitor** — The dashboard shows trends, stock alerts, overdue items, and an activity feed — all scoped to your library.
8. **Library Settings** — Update your library name from the profile page at any time.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push and open a Pull Request

---

**Made with ❤️ by [Noor Butt](https://github.com/noorrbutt)**
