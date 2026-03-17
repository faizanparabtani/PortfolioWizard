"""Tests for generator services: ContentGenerator and ResumeTailor."""
import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.contrib.auth.models import User

from generator.models import PortfolioTemplate
from generator.services.content_generator import PORTFOLIO_SCHEMA, ContentGenerator
from generator.services.resume_tailor import TAILOR_SCHEMA, ResumeTailor

from .conftest import *  # noqa: F401, F403


# ===========================================================================
# Helpers
# ===========================================================================

SAMPLE_PORTFOLIO = {
    "about": "I am a software engineer with 5 years of experience.",
    "skills": ["Python", "Django", "PostgreSQL"],
    "experience": [
        {
            "position": "Senior Developer",
            "company": "Tech Corp",
            "start_date": "2020",
            "end_date": "Present",
            "bullets": ["Built scalable APIs", "Led a team of 4"],
        }
    ],
    "projects": [
        {
            "title": "Portfolio Wizard",
            "technologies": ["Django", "Claude"],
            "bullets": ["Generated portfolios using AI"],
        }
    ],
}

SAMPLE_TAILOR = {
    "summary": "Tailored summary for the role.",
    "skills": ["Django", "Python", "REST APIs"],
    "experience": [
        {
            "position": "Backend Dev",
            "company": "Startup",
            "start_date": "2022",
            "end_date": "2024",
            "bullets": ["Built REST APIs with Django"],
        }
    ],
    "keywords_matched": ["Django", "Python"],
    "keywords_missing": ["Rust", "Go"],
    "ats_score": 78,
    "changes_summary": ["Reordered skills", "Rewrote experience bullets"],
}


def _make_mock_stream(text: str):
    """Return a mock context manager whose get_final_message() returns a text block."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    final_msg = MagicMock()
    final_msg.content = [text_block]

    stream = MagicMock()
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    stream.get_final_message.return_value = final_msg
    return stream


def _make_error_stream(exc):
    """Return a mock stream that raises on get_final_message."""
    stream = MagicMock()
    stream.__enter__ = MagicMock(return_value=stream)
    stream.__exit__ = MagicMock(return_value=False)
    stream.get_final_message.side_effect = exc
    return stream


# ===========================================================================
# ContentGenerator
# ===========================================================================

@pytest.fixture
def content_gen(user, template, settings):
    settings.ANTHROPIC_API_KEY = "fake-key"
    with patch("generator.services.content_generator.anthropic.Anthropic"):
        gen = ContentGenerator("Resume text here", user, template)
    return gen


class TestContentGeneratorInit:
    def test_raises_without_api_key(self, db, user, template, settings):
        settings.ANTHROPIC_API_KEY = None
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ContentGenerator("text", user, template)

    def test_sets_model_to_claude(self, content_gen):
        assert "claude" in content_gen.model

    def test_client_is_set(self, content_gen):
        assert content_gen.client is not None


class TestContentGeneratorGenerate:
    def test_returns_html_and_raw_on_success(self, content_gen, tmp_path, settings):
        (tmp_path / "portfolios" / "modern").mkdir(parents=True)
        (tmp_path / "portfolios" / "modern" / "index.html").write_text(
            "<html><body>{{ about.title }}</body></html>", encoding="utf-8"
        )
        settings.BASE_DIR = tmp_path

        content_gen.client.messages.stream.return_value = _make_mock_stream(
            json.dumps(SAMPLE_PORTFOLIO)
        )

        result = content_gen.generate_content()

        assert "html_content" in result
        assert "raw_content" in result
        assert result["raw_content"]["about"] == SAMPLE_PORTFOLIO["about"]
        assert "testuser" in result["html_content"]

    def test_skills_present_in_raw_content(self, content_gen, tmp_path, settings):
        (tmp_path / "portfolios" / "modern").mkdir(parents=True)
        (tmp_path / "portfolios" / "modern" / "index.html").write_text(
            "<html><body></body></html>", encoding="utf-8"
        )
        settings.BASE_DIR = tmp_path

        content_gen.client.messages.stream.return_value = _make_mock_stream(
            json.dumps(SAMPLE_PORTFOLIO)
        )

        result = content_gen.generate_content()
        assert "Python" in result["raw_content"]["skills"]

    def test_falls_back_to_defaults_on_api_failure(self, content_gen, tmp_path, settings):
        (tmp_path / "portfolios" / "modern").mkdir(parents=True)
        (tmp_path / "portfolios" / "modern" / "index.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        settings.BASE_DIR = tmp_path
        content_gen.client.messages.stream.return_value = _make_error_stream(
            RuntimeError("API down")
        )

        result = content_gen.generate_content()

        assert result["raw_content"]["about"] == "Professional summary not available."
        assert result["raw_content"]["experience"] == []

    def test_portfolio_schema_required_fields(self):
        for field in ("about", "skills", "experience", "projects"):
            assert field in PORTFOLIO_SCHEMA["required"]

    def test_portfolio_schema_uses_lowercase_types(self):
        assert PORTFOLIO_SCHEMA["type"] == "object"
        assert PORTFOLIO_SCHEMA["properties"]["skills"]["type"] == "array"


# ===========================================================================
# ResumeTailor
# ===========================================================================

@pytest.fixture
def tailor(settings):
    settings.ANTHROPIC_API_KEY = "fake-key"
    with patch("generator.services.resume_tailor.anthropic.Anthropic"):
        t = ResumeTailor("My resume text", "Job description here")
    return t


class TestResumeTailorInit:
    def test_raises_without_api_key(self, settings):
        settings.ANTHROPIC_API_KEY = None
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            ResumeTailor("resume", "jd")

    def test_sets_model(self, tailor):
        assert "claude" in tailor.model


class TestResumeTailorTailor:
    def test_returns_structured_dict(self, tailor):
        tailor.client.messages.stream.return_value = _make_mock_stream(
            json.dumps(SAMPLE_TAILOR)
        )

        result = tailor.tailor()

        assert result["summary"] == SAMPLE_TAILOR["summary"]
        assert result["ats_score"] == 78
        assert "Django" in result["keywords_matched"]
        assert "Rust" in result["keywords_missing"]

    def test_raises_on_empty_response(self, tailor):
        # Empty text block
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = ""
        final_msg = MagicMock()
        final_msg.content = [text_block]
        stream = MagicMock()
        stream.__enter__ = MagicMock(return_value=stream)
        stream.__exit__ = MagicMock(return_value=False)
        stream.get_final_message.return_value = final_msg

        tailor.client.messages.stream.return_value = stream

        with pytest.raises(ValueError, match="Empty response"):
            tailor.tailor()

    def test_raises_on_api_error(self, tailor):
        tailor.client.messages.stream.return_value = _make_error_stream(
            RuntimeError("API error")
        )
        with pytest.raises(RuntimeError):
            tailor.tailor()

    def test_tailor_schema_required_fields(self):
        for field in ("summary", "skills", "experience", "keywords_matched",
                      "keywords_missing", "ats_score", "changes_summary"):
            assert field in TAILOR_SCHEMA["required"]

    def test_prompt_includes_resume_and_jd(self, tailor):
        tailor.resume_text = "MY RESUME CONTENT"
        tailor.job_description = "UNIQUE JD PHRASE"
        tailor.client.messages.stream.return_value = _make_mock_stream(
            json.dumps(SAMPLE_TAILOR)
        )

        tailor.tailor()

        call_kwargs = tailor.client.messages.stream.call_args.kwargs
        prompt = call_kwargs.get("messages", [{}])[0].get("content", "")
        assert "MY RESUME CONTENT" in prompt
        assert "UNIQUE JD PHRASE" in prompt

    def test_tailor_schema_uses_lowercase_types(self):
        assert TAILOR_SCHEMA["type"] == "object"
        assert TAILOR_SCHEMA["properties"]["skills"]["type"] == "array"
