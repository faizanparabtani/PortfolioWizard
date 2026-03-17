"""Tests for users views."""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.fixture
def user(db):
    return User.objects.create_user(username="authuser", password="pass")


class TestRegisterView:
    def test_register_page_loads(self, client):
        response = client.get(reverse("users:register"))
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_register(self, client, user):
        client.login(username="authuser", password="pass")
        response = client.get(reverse("users:register"))
        assert response.status_code == 302

    def test_register_creates_user(self, client, db):
        response = client.post(
            reverse("users:register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "Str0ng!Pass#99",
                "password2": "Str0ng!Pass#99",
            },
        )
        # Should redirect after successful registration.
        assert response.status_code == 302
        assert User.objects.filter(username="newuser").exists()

    def test_register_with_mismatched_passwords_fails(self, client, db):
        client.post(
            reverse("users:register"),
            {
                "username": "baduser",
                "password1": "Str0ng!Pass#99",
                "password2": "different",
            },
        )
        assert not User.objects.filter(username="baduser").exists()


class TestLoginView:
    def test_login_page_loads(self, client):
        response = client.get(reverse("users:login"))
        assert response.status_code == 200

    def test_authenticated_user_redirected_from_login(self, client, user):
        client.login(username="authuser", password="pass")
        response = client.get(reverse("users:login"))
        assert response.status_code == 302

    def test_valid_login_redirects_to_dashboard(self, client, user):
        response = client.post(
            reverse("users:login"),
            {"username": "authuser", "password": "pass"},
        )
        assert response.status_code == 302
        assert "dashboard" in response["Location"]

    def test_invalid_login_stays_on_page(self, client, user):
        response = client.post(
            reverse("users:login"),
            {"username": "authuser", "password": "wrongpass"},
        )
        assert response.status_code == 200
