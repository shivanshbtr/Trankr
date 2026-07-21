# Trankr

A full-stack personal productivity tracker for goals, milestones, habits, daily priorities, and journaling — built as an installable web app (PWA) with a FastAPI backend and vanilla JS frontend.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red)
![PWA](https://img.shields.io/badge/installable-PWA-7c6dfa)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> **Note:** I run a personal, private instance of this app — registration there is restricted to my own account. The full source is available here for anyone who wants to run their own copy; see [`instruction_manual.txt`](./instruction_manual.txt) for a complete self-hosting walkthrough (free, no coding required).

---

## Features

- **Goals & Milestones** — define goals with weighted milestones and track progress toward each
- **Daily Tasks** — priority-tagged tasks with deadlines, reordering, and completion tracking
- **Habits** — recurring habit tracking with daily logs
- **Journal** — daily thoughts, ideas, and mood entries
- **Daily Targets & Top 3** — set daily targets (study, workout, sleep, etc.) and top 3 priorities
- **Email-verified accounts** — registration requires confirming a one-time code sent to your email before login is enabled
- **Optional single-tenant lock** — restrict registration to specific email address(es) via config, or leave open for multi-user self-hosting
- **JWT authentication** — token-based sessions with hashed passwords
- **Installable PWA** — add to your phone or desktop home screen and use it like a native app
- **Single-origin deployment** — one backend serves both the API and the UI, no separate hosting needed

## Tech Stack

| Layer    | Technology                                                        |
| -------- | ----------------------------------------------------------------- |
| Backend  | FastAPI, SQLAlchemy                                               |
| Database | SQLite (dev) / PostgreSQL (production, via psycopg2)              |
| Auth     | JWT (python-jose), passlib (sha256_crypt), email OTP verification |
| Email    | SMTP (any provider — Gmail, Resend, etc.)                        |
| Frontend | Vanilla HTML/CSS/JS single-page app, Chart.js                     |
| PWA      | Web App Manifest + Service Worker                                 |

## Project Structure

```
trankr/
├── backend/
│   ├── main.py            FastAPI app entry point, serves frontend + API
│   ├── database.py        SQLAlchemy engine (env-configurable)
│   ├── models.py          ORM table definitions
│   ├── schemas.py         Pydantic request/response models
│   ├── auth.py            JWT, password hashing, OTP generation
│   ├── email_utils.py     Sends OTP verification emails via SMTP
│   ├── routes/            goals, tasks, habits/journal/targets routers
│   ├── requirements.txt
│   └── .env.example       Template for local secrets (never commit the real .env)
├── frontend/
│   ├── index.html         Single-page app (all features)
│   ├── manifest.json      PWA manifest
│   ├── sw.js              Service worker
│   └── icons/
├── run.py                 One-command local launcher
├── instruction_manual.txt Self-hosting walkthrough for running your own copy
├── runtime.txt            Pins Python version for deployment platforms (e.g. Render)
├── .gitignore
└── README.md
```

## Getting Started

**Requirements:** Python 3.9+

```bash
git clone https://github.com/shivanshbtr/trankr.git
cd trankr/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `http://localhost:8000` — the backend serves the frontend directly. By default the app uses a local SQLite database; set a `DATABASE_URL` environment variable to point it at PostgreSQL instead (see `backend/.env.example`).

**Note on email verification:** registration requires confirming a one-time code sent by email. Without SMTP configured (see `backend/.env.example`), the code is printed to the server console instead — sufficient for local development, but a real SMTP provider is needed for a deployed instance. See `instruction_manual.txt` for a full walkthrough.

## Deployment

`runtime.txt` pins the Python version to 3.11.9 for platforms like Render that otherwise default to the latest Python. This avoids build failures from dependencies (e.g. `pydantic-core`) lacking prebuilt wheels for newer Python versions.

## API

Interactive API docs (Swagger UI) are available at `/docs` once the server is running.

## Future Enhancements Roadmap

- [ ] AI-generated insights from tracked data
- [ ] Data export/import
- [ ] Mobile push notifications for habit reminders
