from django.db import models
from django.conf import settings
import os

# Create your models here.

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
    title = models.CharField(max_length=255)
    description = models.TextField()
    generated_content = models.JSONField()  # Store AI-generated content
    portfolio_folder = models.CharField(max_length=255)  # Path to generated portfolio
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s portfolio - {self.title}"

    def get_portfolio_url(self):
        return f"/portfolios/{self.id}/"
