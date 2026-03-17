"""Tests for all generator models."""
import hashlib
import uuid

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

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
# GeneratedPortfolio
# ===========================================================================

class TestGeneratedPortfolioModel:
    def test_public_slug_is_uuid(self, portfolio):
        assert isinstance(portfolio.public_slug, uuid.UUID)

    def test_public_slug_unique_per_instance(self, db, user, template, resume):
        p1 = GeneratedPortfolio.objects.create(
            user=user, template=template, resume=resume,
            title="P1", portfolio_folder="portfolios/p1/",
        )
        p2 = GeneratedPortfolio.objects.create(
            user=user, template=template, resume=resume,
            title="P2", portfolio_folder="portfolios/p2/",
        )
        assert p1.public_slug != p2.public_slug

    def test_default_status_is_processing(self, db, user, template, resume):
        p = GeneratedPortfolio.objects.create(
            user=user, template=template, resume=resume,
            title="P", portfolio_folder="portfolios/p/",
        )
        assert p.status == GeneratedPortfolio.STATUS_PROCESSING

    def test_generated_content_defaults_to_empty_dict(self, db, user, template, resume):
        p = GeneratedPortfolio.objects.create(
            user=user, template=template, resume=resume,
            title="P", portfolio_folder="portfolios/p/",
        )
        assert p.generated_content == {}

    def test_str_contains_template_and_username(self, portfolio):
        s = str(portfolio)
        assert "Modern" in s
        assert "testuser" in s

    def test_view_count_zero_initially(self, portfolio):
        assert portfolio.view_count == 0

    def test_view_count_increments(self, portfolio):
        PortfolioView.objects.create(portfolio=portfolio)
        PortfolioView.objects.create(portfolio=portfolio)
        assert portfolio.view_count == 2

    def test_last_viewed_none_initially(self, portfolio):
        assert portfolio.last_viewed is None

    def test_last_viewed_returns_most_recent_timestamp(self, portfolio):
        PortfolioView.objects.create(portfolio=portfolio)
        v2 = PortfolioView.objects.create(portfolio=portfolio)
        assert portfolio.last_viewed == v2.viewed_at


# ===========================================================================
# PortfolioView
# ===========================================================================

class TestPortfolioViewModel:
    def test_str_contains_portfolio_id(self, portfolio):
        v = PortfolioView.objects.create(portfolio=portfolio)
        assert str(portfolio.id) in str(v)

    def test_get_ip_hash_returns_sha256(self, rf):
        request = rf.get("/", REMOTE_ADDR="192.168.1.1")
        expected = hashlib.sha256(b"192.168.1.1").hexdigest()
        assert PortfolioView.get_ip_hash(request) == expected

    def test_get_ip_hash_prefers_x_forwarded_for(self, rf):
        request = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.1, 10.0.0.2", REMOTE_ADDR="127.0.0.1")
        expected = hashlib.sha256(b"10.0.0.1").hexdigest()
        assert PortfolioView.get_ip_hash(request) == expected

    def test_get_ip_hash_empty_when_no_ip(self, rf):
        request = rf.get("/")
        request.META.pop("REMOTE_ADDR", None)
        request.META.pop("HTTP_X_FORWARDED_FOR", None)
        assert PortfolioView.get_ip_hash(request) == ""

    def test_ordering_newest_first(self, portfolio):
        v1 = PortfolioView.objects.create(portfolio=portfolio)
        v2 = PortfolioView.objects.create(portfolio=portfolio)
        views = list(PortfolioView.objects.filter(portfolio=portfolio))
        assert views[0] == v2
        assert views[1] == v1


# ===========================================================================
# TailoredResume
# ===========================================================================

class TestTailoredResumeModel:
    def test_str_contains_role_and_company(self, tailored_resume):
        s = str(tailored_resume)
        assert "Backend Engineer" in s
        assert "Stripe" in s

    def test_str_fallback_without_role(self, db, user, resume):
        t = TailoredResume.objects.create(
            user=user, resume=resume, job_description="JD here",
            tailored_content={},
        )
        assert "Tailored Resume" in str(t)

    def test_ordering_newest_first(self, db, user, resume):
        t1 = TailoredResume.objects.create(
            user=user, resume=resume, job_description="JD1", tailored_content={},
        )
        t2 = TailoredResume.objects.create(
            user=user, resume=resume, job_description="JD2", tailored_content={},
        )
        results = list(TailoredResume.objects.filter(user=user))
        assert results[0] == t2

    def test_tailored_content_defaults_to_empty_dict(self, db, user, resume):
        t = TailoredResume.objects.create(
            user=user, resume=resume, job_description="JD", tailored_content={},
        )
        assert t.tailored_content == {}


# ===========================================================================
# JobApplication
# ===========================================================================

class TestJobApplicationModel:
    def test_str_contains_role_and_company(self, application):
        s = str(application)
        assert "Senior Developer" in s
        assert "Acme Corp" in s

    def test_default_status_is_applied(self, application):
        assert application.status == JobApplication.STATUS_APPLIED

    def test_status_color_applied(self, application):
        assert application.status_color == "blue"

    def test_status_color_interview(self, application):
        application.status = JobApplication.STATUS_INTERVIEW
        assert application.status_color == "yellow"

    def test_status_color_offer(self, application):
        application.status = JobApplication.STATUS_OFFER
        assert application.status_color == "green"

    def test_status_color_rejected(self, application):
        application.status = JobApplication.STATUS_REJECTED
        assert application.status_color == "red"

    def test_status_color_withdrawn(self, application):
        application.status = JobApplication.STATUS_WITHDRAWN
        assert application.status_color == "gray"

    def test_ordering_newest_first(self, db, user, resume):
        a1 = JobApplication.objects.create(user=user, company="A", role="Dev")
        a2 = JobApplication.objects.create(user=user, company="B", role="Dev")
        results = list(JobApplication.objects.filter(user=user))
        assert results[0] == a2

    def test_resume_used_nullable(self, db, user):
        app = JobApplication.objects.create(user=user, company="X", role="Y")
        assert app.resume_used is None

    def test_tailored_resume_set_null_on_delete(self, db, user, resume, tailored_resume):
        app = JobApplication.objects.create(
            user=user, company="X", role="Y", tailored_resume=tailored_resume,
        )
        tailored_resume.delete()
        app.refresh_from_db()
        assert app.tailored_resume is None
