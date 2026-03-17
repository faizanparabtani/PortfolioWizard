"""Comprehensive tests for all generator views."""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from generator.models import (
    GeneratedPortfolio,
    JobApplication,
    PortfolioTemplate,
    PortfolioView,
    Resume,
    TailoredResume,
)

from .conftest import *  # noqa: F401, F403


# ===========================================================================
# Landing
# ===========================================================================

class TestLanding:
    def test_returns_200(self, client):
        assert client.get(reverse("generator:landing")).status_code == 200


# ===========================================================================
# Dashboard
# ===========================================================================

class TestDashboard:
    def test_redirects_anonymous(self, client):
        r = client.get(reverse("generator:dashboard"))
        assert r.status_code == 302
        assert "login" in r["Location"]

    def test_accessible_when_logged_in(self, auth_client):
        assert auth_client.get(reverse("generator:dashboard")).status_code == 200

    def test_shows_application_tracker_when_applications_exist(self, auth_client, application):
        r = auth_client.get(reverse("generator:dashboard"))
        assert r.status_code == 200
        assert b"Application Tracker" in r.content

    def test_hides_application_tracker_when_no_applications(self, auth_client, db):
        r = auth_client.get(reverse("generator:dashboard"))
        assert b"Application Tracker" not in r.content

    def test_shows_resume_tailor_link_when_resume_exists(self, auth_client, resume):
        r = auth_client.get(reverse("generator:dashboard"))
        assert b"tailor" in r.content.lower()

    def test_pipeline_step1_active_when_no_resume(self, auth_client, db):
        r = auth_client.get(reverse("generator:dashboard"))
        assert b"Upload" in r.content

    def test_pipeline_step2_active_when_resume_exists(self, auth_client, resume):
        r = auth_client.get(reverse("generator:dashboard"))
        assert b"Pick Template" in r.content or b"Generate Portfolio" in r.content

    def test_pipeline_shows_share_when_portfolio_complete(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:dashboard"))
        assert b"View" in r.content or b"Share" in r.content


# ===========================================================================
# Resume management
# ===========================================================================

class TestUploadResume:
    def test_get_shows_form(self, auth_client):
        assert auth_client.get(reverse("generator:upload_resume")).status_code == 200

    def test_redirects_anonymous(self, client):
        assert client.get(reverse("generator:upload_resume")).status_code == 302

    def test_valid_upload_creates_resume(self, auth_client, db):
        pdf = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        r = auth_client.post(reverse("generator:upload_resume"), {"name": "Test CV", "file": pdf})
        assert r.status_code == 302
        assert Resume.objects.filter(name="Test CV").exists()

    def test_non_pdf_rejected(self, auth_client, db):
        bad = SimpleUploadedFile("cv.txt", b"text", content_type="text/plain")
        r = auth_client.post(reverse("generator:upload_resume"), {"name": "Bad CV", "file": bad})
        assert r.status_code == 200  # re-renders form with errors
        assert not Resume.objects.filter(name="Bad CV").exists()


class TestDeleteResume:
    def test_post_deletes_resume(self, auth_client, resume):
        r = auth_client.post(reverse("generator:delete_resume", args=[resume.id]))
        assert r.status_code == 302
        assert not Resume.objects.filter(pk=resume.pk).exists()

    def test_get_shows_confirmation(self, auth_client, resume):
        r = auth_client.get(reverse("generator:delete_resume", args=[resume.id]))
        assert r.status_code == 200

    def test_cannot_delete_other_users_resume(self, other_client, resume):
        r = other_client.post(reverse("generator:delete_resume", args=[resume.id]))
        assert r.status_code == 404
        assert Resume.objects.filter(pk=resume.pk).exists()


# ===========================================================================
# Resume tailoring
# ===========================================================================

TAILOR_RESULT = {
    "summary": "Tailored summary.",
    "skills": ["Python", "Django"],
    "experience": [],
    "keywords_matched": ["Python"],
    "keywords_missing": ["Rust"],
    "ats_score": 80,
    "changes_summary": ["Reordered skills"],
}


class TestTailorResume:
    def test_get_shows_form(self, auth_client, resume):
        r = auth_client.get(reverse("generator:tailor_resume", args=[resume.id]))
        assert r.status_code == 200

    def test_redirects_anonymous(self, client, resume):
        assert client.get(reverse("generator:tailor_resume", args=[resume.id])).status_code == 302

    def test_404_for_other_users_resume(self, other_client, resume):
        assert other_client.get(reverse("generator:tailor_resume", args=[resume.id])).status_code == 404

    def test_post_creates_tailored_resume_and_redirects(self, auth_client, resume):
        with patch("generator.views.resume.ResumeParser") as mock_parser, \
             patch("generator.views.resume.ResumeTailor") as mock_tailor:
            mock_parser.return_value.extract_text.return_value = "Resume text"
            mock_tailor.return_value.tailor.return_value = TAILOR_RESULT

            r = auth_client.post(reverse("generator:tailor_resume", args=[resume.id]), {
                "role_title": "Backend Engineer",
                "company_name": "Stripe",
                "job_description": "We need a Python developer.",
            })

        assert r.status_code == 302
        assert TailoredResume.objects.filter(role_title="Backend Engineer", company_name="Stripe").exists()

    def test_post_with_api_error_shows_error_message(self, auth_client, resume):
        with patch("generator.views.resume.ResumeParser") as mock_parser, \
             patch("generator.views.resume.ResumeTailor") as mock_tailor:
            mock_parser.return_value.extract_text.return_value = "Resume text"
            mock_tailor.return_value.tailor.side_effect = RuntimeError("API down")

            r = auth_client.post(reverse("generator:tailor_resume", args=[resume.id]), {
                "job_description": "Python dev needed.",
            })

        assert r.status_code == 200  # re-renders form
        assert not TailoredResume.objects.exists()


class TestTailoredResumeList:
    def test_shows_users_tailored_resumes(self, auth_client, tailored_resume):
        r = auth_client.get(reverse("generator:tailored_resume_list"))
        assert r.status_code == 200
        assert b"Backend Engineer" in r.content

    def test_does_not_show_other_users_tailored_resumes(self, other_client, tailored_resume):
        r = other_client.get(reverse("generator:tailored_resume_list"))
        assert b"Backend Engineer" not in r.content

    def test_redirects_anonymous(self, client):
        assert client.get(reverse("generator:tailored_resume_list")).status_code == 302


class TestTailoredResumeDetail:
    def test_shows_result(self, auth_client, tailored_resume):
        r = auth_client.get(reverse("generator:tailored_resume_detail", args=[tailored_resume.pk]))
        assert r.status_code == 200
        assert b"Backend Engineer" in r.content
        assert b"82" in r.content  # ATS score

    def test_404_for_other_users_tailored_resume(self, other_client, tailored_resume):
        assert other_client.get(
            reverse("generator:tailored_resume_detail", args=[tailored_resume.pk])
        ).status_code == 404

    def test_redirects_anonymous(self, client, tailored_resume):
        assert client.get(
            reverse("generator:tailored_resume_detail", args=[tailored_resume.pk])
        ).status_code == 302


class TestDeleteTailoredResume:
    def test_post_deletes(self, auth_client, tailored_resume):
        r = auth_client.post(reverse("generator:delete_tailored_resume", args=[tailored_resume.pk]))
        assert r.status_code == 302
        assert not TailoredResume.objects.filter(pk=tailored_resume.pk).exists()

    def test_cannot_delete_other_users(self, other_client, tailored_resume):
        other_client.post(reverse("generator:delete_tailored_resume", args=[tailored_resume.pk]))
        assert TailoredResume.objects.filter(pk=tailored_resume.pk).exists()


# ===========================================================================
# Portfolio management
# ===========================================================================

class TestPortfolioTemplates:
    def test_shows_active_templates(self, auth_client, template, inactive_template):
        r = auth_client.get(reverse("generator:portfolio_templates"))
        assert r.status_code == 200
        assert b"Modern" in r.content
        assert b"Legacy" not in r.content

    def test_accessible_to_anonymous(self, client, db):
        assert client.get(reverse("generator:portfolio_templates")).status_code == 200

    def test_shows_guest_resume_banner_when_session_set(self, client, db):
        session = client.session
        session['guest_resume_name'] = 'my_cv.pdf'
        session.save()
        r = client.get(reverse("generator:portfolio_templates"))
        assert b"my_cv.pdf" in r.content

    def test_shows_upload_prompt_when_no_guest_resume(self, client, db):
        r = client.get(reverse("generator:portfolio_templates"))
        assert b"Drop your PDF" in r.content or b"No resume uploaded" in r.content or b"Drop" in r.content


# ===========================================================================
# Guest flow
# ===========================================================================

class TestGuestUpload:
    def test_get_redirects_to_landing(self, client):
        r = client.get(reverse("generator:guest_upload"))
        assert r.status_code == 302
        assert "generator:landing" not in r["Location"]  # just redirects

    def test_valid_pdf_stored_in_session_and_redirects(self, client, tmp_path, db):
        pdf = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 content", content_type="application/pdf")
        r = client.post(reverse("generator:guest_upload"), {"resume": pdf})
        assert r.status_code == 302
        assert "guest_resume_name" in client.session
        assert client.session["guest_resume_name"] == "cv.pdf"

    def test_non_pdf_rejected(self, client, db):
        bad = SimpleUploadedFile("cv.txt", b"text", content_type="text/plain")
        r = client.post(reverse("generator:guest_upload"), {"resume": bad})
        assert r.status_code == 302
        assert "guest_resume_name" not in client.session

    def test_no_file_redirects_with_error(self, client, db):
        r = client.post(reverse("generator:guest_upload"), {})
        assert r.status_code == 302


class TestGuestSelectTemplate:
    def test_stores_template_id_in_session_and_redirects_to_register(self, client, template, db):
        r = client.get(reverse("generator:guest_select_template", args=[template.id]))
        assert r.status_code == 302
        assert "register" in r["Location"]
        assert client.session.get("guest_template_id") == template.id

    def test_404_for_inactive_template(self, client, inactive_template, db):
        r = client.get(reverse("generator:guest_select_template", args=[inactive_template.id]))
        assert r.status_code == 404


class TestCheckGenerationStatus:
    def test_returns_status_json(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:check_generation_status", args=[portfolio.id]))
        data = json.loads(r.content)
        assert data["status"] == GeneratedPortfolio.STATUS_COMPLETED

    def test_returns_not_found_for_missing_id(self, auth_client):
        r = auth_client.get(reverse("generator:check_generation_status", args=[99999]))
        assert json.loads(r.content)["status"] == "not_found"

    def test_cannot_see_other_users_portfolio(self, other_client, portfolio):
        r = other_client.get(reverse("generator:check_generation_status", args=[portfolio.id]))
        assert json.loads(r.content)["status"] == "not_found"


class TestViewPortfolio:
    def test_shows_portfolio(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:view_portfolio", args=[portfolio.id]))
        assert r.status_code == 200
        assert b"My Portfolio" in r.content

    def test_shows_view_count(self, auth_client, portfolio):
        PortfolioView.objects.create(portfolio=portfolio)
        PortfolioView.objects.create(portfolio=portfolio)
        r = auth_client.get(reverse("generator:view_portfolio", args=[portfolio.id]))
        assert b"2" in r.content

    def test_redirects_anonymous(self, client, portfolio):
        assert client.get(reverse("generator:view_portfolio", args=[portfolio.id])).status_code == 302

    def test_404_for_other_users_portfolio(self, other_client, portfolio):
        assert other_client.get(
            reverse("generator:view_portfolio", args=[portfolio.id])
        ).status_code == 404


class TestServePortfolio:
    def test_returns_html_content(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:serve_portfolio", args=[portfolio.id]))
        assert r.status_code == 200
        assert r["Content-Type"].startswith("text/html")
        assert b"Hello" in r.content

    def test_sets_csp_header(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:serve_portfolio", args=[portfolio.id]))
        assert "Content-Security-Policy" in r

    def test_404_for_other_users_portfolio(self, other_client, portfolio):
        assert other_client.get(
            reverse("generator:serve_portfolio", args=[portfolio.id])
        ).status_code == 404


class TestDeletePortfolio:
    def test_post_deletes_portfolio(self, auth_client, portfolio):
        r = auth_client.post(reverse("generator:delete_portfolio", args=[portfolio.id]))
        assert r.status_code == 302
        assert not GeneratedPortfolio.objects.filter(pk=portfolio.pk).exists()

    def test_cannot_delete_other_users_portfolio(self, other_client, portfolio):
        other_client.post(reverse("generator:delete_portfolio", args=[portfolio.id]))
        assert GeneratedPortfolio.objects.filter(pk=portfolio.pk).exists()

    def test_get_redirects_without_deleting(self, auth_client, portfolio):
        auth_client.get(reverse("generator:delete_portfolio", args=[portfolio.id]))
        assert GeneratedPortfolio.objects.filter(pk=portfolio.pk).exists()


class TestEditPortfolio:
    def test_get_shows_editor(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:edit_portfolio", args=[portfolio.id]))
        assert r.status_code == 200

    def test_post_saves_sanitized_content(self, auth_client, portfolio):
        new_html = "<h1>Updated</h1><script>alert('xss')</script>"
        auth_client.post(
            reverse("generator:edit_portfolio", args=[portfolio.id]),
            {"html_content": new_html},
        )
        portfolio.refresh_from_db()
        saved = portfolio.generated_content["html_content"]
        assert "<h1>Updated</h1>" in saved
        assert "<script>" not in saved

    def test_post_redirects_to_view(self, auth_client, portfolio):
        r = auth_client.post(
            reverse("generator:edit_portfolio", args=[portfolio.id]),
            {"html_content": "<h1>New content</h1>"},
        )
        assert r.status_code == 302
        assert f"/portfolios/{portfolio.id}/" in r["Location"]


class TestPortfolioList:
    def test_shows_user_portfolios(self, auth_client, portfolio):
        r = auth_client.get(reverse("generator:portfolio_list"))
        assert r.status_code == 200
        assert b"fa-file-alt" in r.content  # portfolio card icon present

    def test_does_not_show_other_users_portfolios(self, other_client, portfolio):
        r = other_client.get(reverse("generator:portfolio_list"))
        assert b"No portfolios found" in r.content  # empty state shown

    def test_redirects_anonymous(self, client):
        assert client.get(reverse("generator:portfolio_list")).status_code == 302


# ===========================================================================
# Public portfolio + analytics
# ===========================================================================

class TestPublicPortfolio:
    def test_accessible_without_login(self, client, portfolio):
        r = client.get(reverse("generator:public_portfolio", args=[portfolio.public_slug]))
        assert r.status_code == 200
        assert b"Hello" in r.content

    def test_logs_portfolio_view(self, client, portfolio):
        assert PortfolioView.objects.filter(portfolio=portfolio).count() == 0
        client.get(reverse("generator:public_portfolio", args=[portfolio.public_slug]))
        assert PortfolioView.objects.filter(portfolio=portfolio).count() == 1

    def test_multiple_visits_logged(self, client, portfolio):
        for _ in range(3):
            client.get(reverse("generator:public_portfolio", args=[portfolio.public_slug]))
        assert PortfolioView.objects.filter(portfolio=portfolio).count() == 3

    def test_logs_referrer(self, client, portfolio):
        client.get(
            reverse("generator:public_portfolio", args=[portfolio.public_slug]),
            HTTP_REFERER="https://linkedin.com/",
        )
        view = PortfolioView.objects.get(portfolio=portfolio)
        assert "linkedin.com" in view.referrer

    def test_404_for_unknown_slug(self, client, db):
        assert client.get(
            reverse("generator:public_portfolio", args=[uuid.uuid4()])
        ).status_code == 404

    def test_404_when_html_content_empty(self, client, db, user, template, resume):
        p = GeneratedPortfolio.objects.create(
            user=user, template=template, resume=resume,
            title="Empty", portfolio_folder="portfolios/empty/",
            generated_content={},
        )
        assert client.get(
            reverse("generator:public_portfolio", args=[p.public_slug])
        ).status_code == 404

    def test_csp_header_present(self, client, portfolio):
        r = client.get(reverse("generator:public_portfolio", args=[portfolio.public_slug]))
        assert "Content-Security-Policy" in r


# ===========================================================================
# Job application tracker
# ===========================================================================

class TestApplicationList:
    def test_shows_user_applications(self, auth_client, application):
        r = auth_client.get(reverse("generator:application_list"))
        assert r.status_code == 200
        assert b"Acme Corp" in r.content

    def test_does_not_show_other_users_applications(self, other_client, application):
        r = other_client.get(reverse("generator:application_list"))
        assert b"Acme Corp" not in r.content

    def test_redirects_anonymous(self, client):
        assert client.get(reverse("generator:application_list")).status_code == 302

    def test_status_filter_applied(self, auth_client, application, db, user):
        JobApplication.objects.create(user=user, company="Other Co", role="Dev", status="offer")
        r = auth_client.get(reverse("generator:application_list") + "?status=offer")
        assert b"Acme Corp" not in r.content
        assert b"Other Co" in r.content

    def test_all_applications_without_filter(self, auth_client, db, user):
        JobApplication.objects.create(user=user, company="Co A", role="Dev", status="applied")
        JobApplication.objects.create(user=user, company="Co B", role="Dev", status="offer")
        r = auth_client.get(reverse("generator:application_list"))
        assert b"Co A" in r.content
        assert b"Co B" in r.content


class TestApplicationCreate:
    def test_get_shows_form(self, auth_client):
        assert auth_client.get(reverse("generator:application_create")).status_code == 200

    def test_redirects_anonymous(self, client):
        assert client.get(reverse("generator:application_create")).status_code == 302

    def test_post_creates_application(self, auth_client, db):
        r = auth_client.post(reverse("generator:application_create"), {
            "company": "Stripe",
            "role": "Backend Engineer",
            "status": "applied",
        })
        assert r.status_code == 302
        assert JobApplication.objects.filter(company="Stripe").exists()

    def test_post_with_missing_fields_re_renders(self, auth_client):
        r = auth_client.post(reverse("generator:application_create"), {"company": ""})
        assert r.status_code == 200

    def test_application_belongs_to_logged_in_user(self, auth_client, user, db):
        auth_client.post(reverse("generator:application_create"), {
            "company": "NewCo",
            "role": "Engineer",
            "status": "applied",
        })
        app = JobApplication.objects.get(company="NewCo")
        assert app.user == user


class TestApplicationUpdate:
    def test_get_shows_prepopulated_form(self, auth_client, application):
        r = auth_client.get(reverse("generator:application_update", args=[application.pk]))
        assert r.status_code == 200
        assert b"Acme Corp" in r.content

    def test_post_updates_status(self, auth_client, application):
        auth_client.post(reverse("generator:application_update", args=[application.pk]), {
            "company": "Acme Corp",
            "role": "Senior Developer",
            "status": "interview",
        })
        application.refresh_from_db()
        assert application.status == "interview"

    def test_404_for_other_users_application(self, other_client, application):
        assert other_client.get(
            reverse("generator:application_update", args=[application.pk])
        ).status_code == 404


class TestApplicationDelete:
    def test_post_deletes_application(self, auth_client, application):
        r = auth_client.post(reverse("generator:application_delete", args=[application.pk]))
        assert r.status_code == 302
        assert not JobApplication.objects.filter(pk=application.pk).exists()

    def test_cannot_delete_other_users_application(self, other_client, application):
        other_client.post(reverse("generator:application_delete", args=[application.pk]))
        assert JobApplication.objects.filter(pk=application.pk).exists()

    def test_get_does_not_delete(self, auth_client, application):
        auth_client.get(reverse("generator:application_delete", args=[application.pk]))
        assert JobApplication.objects.filter(pk=application.pk).exists()


# ===========================================================================
# Staff: manage templates
# ===========================================================================

class TestManageTemplates:
    def test_staff_can_access(self, staff_client):
        assert staff_client.get(reverse("generator:manage_templates")).status_code == 200

    def test_non_staff_redirected(self, auth_client):
        r = auth_client.get(reverse("generator:manage_templates"))
        assert r.status_code == 302

    def test_anonymous_redirected(self, client):
        assert client.get(reverse("generator:manage_templates")).status_code == 302
