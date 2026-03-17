"""Shared pytest fixtures for generator tests."""
import pytest
from django.contrib.auth.models import User
from django.core.files import File

from generator.models import GeneratedPortfolio, JobApplication, PortfolioTemplate, Resume, TailoredResume


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass", email="t@test.com")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="pass")


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username="staff", password="pass", is_staff=True)


# ---------------------------------------------------------------------------
# Core objects
# ---------------------------------------------------------------------------

@pytest.fixture
def template(db):
    return PortfolioTemplate.objects.create(
        name="Modern",
        description="A modern template",
        template_folder="portfolios/modern/",
        thumbnail="thumbnails/placeholder.jpg",
        is_active=True,
    )


@pytest.fixture
def inactive_template(db):
    return PortfolioTemplate.objects.create(
        name="Legacy",
        description="Old template",
        template_folder="portfolios/legacy/",
        thumbnail="thumbnails/placeholder.jpg",
        is_active=False,
    )


@pytest.fixture
def resume(db, user, tmp_path):
    fake_pdf = tmp_path / "cv.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")
    r = Resume(user=user, name="My CV")
    r.file.save("cv.pdf", File(fake_pdf.open("rb")), save=True)
    return r


@pytest.fixture
def portfolio(db, user, template, resume):
    return GeneratedPortfolio.objects.create(
        user=user,
        template=template,
        resume=resume,
        title="My Portfolio",
        portfolio_folder="portfolios/testuser_Modern/",
        status=GeneratedPortfolio.STATUS_COMPLETED,
        generated_content={"html_content": "<html><body><h1>Hello</h1></body></html>"},
    )


@pytest.fixture
def tailored_resume(db, user, resume):
    return TailoredResume.objects.create(
        user=user,
        resume=resume,
        company_name="Stripe",
        role_title="Backend Engineer",
        job_description="We need a Python expert.",
        tailored_content={
            "summary": "Experienced engineer.",
            "skills": ["Python", "Django"],
            "experience": [],
            "keywords_matched": ["Python"],
            "keywords_missing": ["Rust"],
            "ats_score": 82,
            "changes_summary": ["Reordered skills"],
        },
    )


@pytest.fixture
def application(db, user, resume):
    return JobApplication.objects.create(
        user=user,
        company="Acme Corp",
        role="Senior Developer",
        status=JobApplication.STATUS_APPLIED,
        resume_used=resume,
    )


# ---------------------------------------------------------------------------
# Authenticated clients
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_client(client, user):
    client.login(username="testuser", password="pass")
    return client


@pytest.fixture
def other_client(client, other_user):
    client.login(username="otheruser", password="pass")
    return client


@pytest.fixture
def staff_client(client, staff_user):
    client.login(username="staff", password="pass")
    return client
