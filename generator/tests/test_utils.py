"""Tests for generator.utils.sanitize_html."""
import pytest

from generator.utils import sanitize_html


class TestSanitizeHtml:
    def test_strips_script_tags(self):
        dirty = "<p>Hello</p><script>alert('xss')</script>"
        assert "<script>" not in sanitize_html(dirty)
        assert "<p>Hello</p>" in sanitize_html(dirty)

    def test_strips_inline_event_handlers_double_quotes(self):
        dirty = '<img src="x" onerror="alert(1)">'
        result = sanitize_html(dirty)
        assert "onerror" not in result

    def test_strips_inline_event_handlers_single_quotes(self):
        dirty = "<a onclick='evil()'>click</a>"
        result = sanitize_html(dirty)
        assert "onclick" not in result

    def test_strips_javascript_urls(self):
        dirty = '<a href="javascript:void(0)">link</a>'
        result = sanitize_html(dirty)
        assert "javascript:" not in result

    def test_preserves_safe_html(self):
        safe = "<h1>Title</h1><p>Paragraph with <strong>bold</strong> text.</p>"
        assert sanitize_html(safe) == safe

    def test_empty_string_returns_empty_string(self):
        assert sanitize_html("") == ""
