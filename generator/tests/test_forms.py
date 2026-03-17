"""Tests for generator forms."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from generator.forms import JobApplicationForm, ResumeUploadForm, TailorResumeForm
from generator.models import JobApplication

from .conftest import *  # noqa: F401, F403


def make_pdf(size_bytes=1024):
    """Return a fake PDF SimpleUploadedFile of a given size."""
    content = b"%PDF-1.4 " + b"x" * max(0, size_bytes - 9)
    return SimpleUploadedFile("cv.pdf", content, content_type="application/pdf")


def make_file(name="file.txt", content=b"data", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


# ===========================================================================
# ResumeUploadForm
# ===========================================================================

class TestResumeUploadForm:
    def test_valid_pdf_passes(self):
        form = ResumeUploadForm(
            data={"name": "My CV"},
            files={"file": make_pdf()},
        )
        assert form.is_valid(), form.errors

    def test_non_pdf_extension_rejected(self):
        form = ResumeUploadForm(
            data={"name": "My CV"},
            files={"file": make_file("resume.docx", b"data", "application/msword")},
        )
        assert not form.is_valid()
        assert "file" in form.errors

    def test_file_over_5mb_rejected(self):
        big_file = make_pdf(size_bytes=6 * 1024 * 1024)
        form = ResumeUploadForm(
            data={"name": "Big CV"},
            files={"file": big_file},
        )
        assert not form.is_valid()
        assert "file" in form.errors

    def test_file_exactly_5mb_passes(self):
        file_at_limit = make_pdf(size_bytes=5 * 1024 * 1024)
        form = ResumeUploadForm(
            data={"name": "Big CV"},
            files={"file": file_at_limit},
        )
        assert form.is_valid(), form.errors

    def test_missing_file_invalid(self):
        form = ResumeUploadForm(data={"name": "My CV"}, files={})
        assert not form.is_valid()


# ===========================================================================
# TailorResumeForm
# ===========================================================================

class TestTailorResumeForm:
    def test_valid_with_just_job_description(self):
        form = TailorResumeForm(data={"job_description": "We need a Python dev."})
        assert form.is_valid(), form.errors

    def test_valid_with_all_fields(self):
        form = TailorResumeForm(data={
            "job_description": "Python developer needed.",
            "role_title": "Backend Engineer",
            "company_name": "Stripe",
        })
        assert form.is_valid(), form.errors

    def test_missing_job_description_invalid(self):
        form = TailorResumeForm(data={"role_title": "Engineer", "company_name": "Acme"})
        assert not form.is_valid()
        assert "job_description" in form.errors

    def test_optional_fields_not_required(self):
        form = TailorResumeForm(data={"job_description": "JD here", "role_title": "", "company_name": ""})
        assert form.is_valid(), form.errors


# ===========================================================================
# JobApplicationForm
# ===========================================================================

class TestJobApplicationForm:
    def test_valid_minimal_form(self, user):
        form = JobApplicationForm(user, data={
            "company": "Acme",
            "role": "Dev",
            "status": JobApplication.STATUS_APPLIED,
        })
        assert form.is_valid(), form.errors

    def test_valid_full_form(self, user, resume):
        form = JobApplicationForm(user, data={
            "company": "Stripe",
            "role": "Backend Engineer",
            "status": JobApplication.STATUS_INTERVIEW,
            "job_url": "https://stripe.com/jobs/123",
            "applied_at": "2026-03-01",
            "resume_used": resume.pk,
            "tailored_resume": "",
            "notes": "Call scheduled for Tuesday.",
        })
        assert form.is_valid(), form.errors

    def test_missing_company_invalid(self, user):
        form = JobApplicationForm(user, data={"role": "Dev", "status": "applied"})
        assert not form.is_valid()
        assert "company" in form.errors

    def test_missing_role_invalid(self, user):
        form = JobApplicationForm(user, data={"company": "Acme", "status": "applied"})
        assert not form.is_valid()
        assert "role" in form.errors

    def test_resume_queryset_scoped_to_user(self, user, other_user, resume, db, tmp_path):
        """Other user's resumes must not appear in the queryset."""
        from django.core.files import File
        other_pdf = tmp_path / "other.pdf"
        other_pdf.write_bytes(b"%PDF-1.4 other")
        from generator.models import Resume
        other_resume = Resume(user=other_user, name="Other CV")
        other_resume.file.save("other.pdf", File(other_pdf.open("rb")), save=True)

        form = JobApplicationForm(user, data={"company": "X", "role": "Y", "status": "applied"})
        qs = form.fields["resume_used"].queryset
        assert resume in qs
        assert other_resume not in qs

    def test_invalid_status_choice_rejected(self, user):
        form = JobApplicationForm(user, data={
            "company": "Acme", "role": "Dev", "status": "flying",
        })
        assert not form.is_valid()
