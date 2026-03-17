# PortfolioWizard

A full-stack Django application that turns a PDF resume into a live, shareable portfolio website using Claude AI — with a second tool that tailors your resume to any job description and returns an ATS compatibility score.

**Live demo:** *(deploy and add link here)*

---

## What it does

### 1. AI Portfolio Generator
Upload a PDF resume. Claude (Anthropic) parses it into structured JSON — skills, experience, projects, about — and populates a professional HTML template. The result is published instantly at a unique public URL (`/p/<uuid>/`) with no external hosting required.

Guests can drop a PDF on the landing page, pick a template, and register in one flow. On sign-up, PortfolioWizard automatically generates the portfolio and redirects to a live loading screen.

### 2. AI Resume Tailor
Paste a job description alongside your uploaded resume. Claude rewrites your experience bullets to match the role, identifies keywords present and missing, and returns an ATS score out of 100. Each tailored version is saved and labelled by company and role for future reference.

### Supporting features
- **Job Application Tracker** — log applications with status (Applied → Interview → Offer → Rejected), link the resume and tailored version used
- **Portfolio Analytics** — every visit to a public portfolio is logged (privacy-safe SHA-256 hashed IP); view count and last-viewed date shown on the dashboard
- **Template management** — staff admin can add/toggle portfolio HTML templates without touching code

---

## Technical highlights

| Concern | Approach |
|---|---|
| AI integration | `anthropic` SDK with adaptive thinking, streaming, and `output_config` JSON schema — structured output, no prompt parsing |
| Guest flow | Landing-page drop zone stores PDF + template choice in session; `_consume_guest_session()` in `users/views.py` auto-generates on first login/register |
| Data isolation | All user-scoped views use `get_object_or_404(..., user=request.user)` — 404 not 403 |
| Privacy | IP addresses hashed with SHA-256 before storage, never stored raw |
| Security | Portfolio HTML served with a strict `Content-Security-Policy`; edit saves sanitised through `bleach` |
| Testing | 162 pytest tests across models, forms, views, services, and template tags — all passing |
| Deployment | Docker + Railway/Render with split settings (`base` / `development` / `production`) |

---

## Stack

- **Backend:** Django 5.2, Python 3.12
- **AI:** Claude Opus 4.6 via `anthropic` SDK (adaptive thinking, structured JSON output, streaming)
- **Database:** PostgreSQL (prod) / SQLite (dev)
- **Frontend:** Tailwind CSS (dark theme, no JS framework)
- **Storage:** Local (dev) / configurable for S3
- **Testing:** pytest-django, unittest.mock
- **Deployment:** Docker, Railway, Render

---

## Running locally

```bash
git clone https://github.com/yourname/PortfolioWizard
cd PortfolioWizard

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser  # optional, for template management
uv run python manage.py runserver
```

Then visit `http://localhost:8000`. You can drop a PDF resume directly on the landing page — no account needed until you generate.

---

## Running tests

```bash
uv run pytest
```

162 tests, all passing.

---

## Project structure

```
generator/
├── services/
│   ├── content_generator.py   # Claude AI portfolio generation (structured JSON output)
│   ├── resume_tailor.py       # Claude AI ATS resume tailoring
│   ├── resume_parser.py       # PDF text extraction
│   └── portfolio_generator.py # Orchestrates generation + template population
├── models.py                  # Resume, PortfolioTemplate, GeneratedPortfolio,
│                              # TailoredResume, JobApplication, PortfolioView
├── views.py                   # All feature views (guest flow, portfolios, applications)
├── forms.py                   # Upload, tailor, application forms
└── templatetags/
    └── generator_tags.py      # get_item, is_textarea filters

portfolios/
├── minimal/index.html         # Light template (Inter, card layout)
└── modern/index.html          # Dark template (gradient accents, glow effects)

portfolio_site_generator/settings/
├── base.py                    # Shared settings
├── development.py             # DEBUG=True, SQLite, load_dotenv
└── production.py              # Validates secrets, security headers, HTTPS
```

---

## License

MIT
