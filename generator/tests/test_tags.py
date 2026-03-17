"""Tests for generator template tags."""
import pytest
from generator.templatetags.generator_tags import get_item


class TestGetItemFilter:
    def test_returns_existing_value(self):
        assert get_item({"a": 5}, "a") == 5

    def test_returns_zero_for_missing_key(self):
        assert get_item({"a": 1}, "b") == 0

    def test_works_with_integer_values(self):
        d = {"applied": 3, "interview": 1, "offer": 0}
        assert get_item(d, "applied") == 3
        assert get_item(d, "offer") == 0

    def test_works_with_empty_dict(self):
        assert get_item({}, "anything") == 0

    def test_returns_string_values(self):
        assert get_item({"key": "value"}, "key") == "value"
