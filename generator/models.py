from django.db import models
from django.conf import settings
import os


class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username}'s resume - {self.name}"

class PortfolioTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    template_folder = models.CharField(max_length=255)  # Path to template files
    thumbnail = models.ImageField(upload_to='portfolio_templates/thumbnails/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GeneratedPortfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    template = models.ForeignKey(PortfolioTemplate, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    generated_content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    portfolio_folder = models.CharField(max_length=255)
    netlify_site_id = models.CharField(max_length=100, blank=True, null=True)
    netlify_deploy_id = models.CharField(max_length=100, blank=True, null=True)
    netlify_url = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s {self.template.name} Portfolio"

    def get_portfolio_url(self):
        """Return the URL to view the generated portfolio"""
        return f"/generator/portfolios/{self.id}/view/"
