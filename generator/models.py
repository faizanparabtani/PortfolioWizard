import hashlib
import uuid

from django.conf import settings
from django.db import models


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
    template_folder = models.CharField(max_length=255)
    thumbnail = models.ImageField(upload_to='portfolio_templates/thumbnails/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GeneratedPortfolio(models.Model):
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ERROR, 'Error'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    template = models.ForeignKey(PortfolioTemplate, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    generated_content = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSING)
    status_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    public_slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_published = models.BooleanField(default=False)
    portfolio_folder = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username}'s {self.template.name} Portfolio"

    def get_portfolio_url(self):
        return f"/generator/portfolios/{self.id}/view/"

    @property
    def view_count(self):
        return self.views.count()

    @property
    def last_viewed(self):
        latest = self.views.order_by('-viewed_at').first()
        return latest.viewed_at if latest else None


class PortfolioView(models.Model):
    """Logs each public hit on a portfolio for analytics."""
    portfolio = models.ForeignKey(
        GeneratedPortfolio, on_delete=models.CASCADE, related_name='views'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    referrer = models.CharField(max_length=500, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f"View of {self.portfolio_id} at {self.viewed_at}"

    @staticmethod
    def get_ip_hash(request):
        ip = (
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or request.META.get('REMOTE_ADDR', '')
        )
        return hashlib.sha256(ip.encode()).hexdigest() if ip else ''


class TailoredResume(models.Model):
    """A resume tailored by AI to match a specific job description."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200, blank=True)
    role_title = models.CharField(max_length=200, blank=True)
    job_description = models.TextField()
    tailored_content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        label = f"{self.role_title} at {self.company_name}" if self.role_title else "Tailored Resume"
        return f"{self.user.username} — {label}"


class JobApplication(models.Model):
    STATUS_APPLIED = 'applied'
    STATUS_INTERVIEW = 'interview'
    STATUS_OFFER = 'offer'
    STATUS_REJECTED = 'rejected'
    STATUS_WITHDRAWN = 'withdrawn'
    STATUS_CHOICES = [
        (STATUS_APPLIED, 'Applied'),
        (STATUS_INTERVIEW, 'Interview'),
        (STATUS_OFFER, 'Offer'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    STATUS_COLORS = {
        STATUS_APPLIED: 'blue',
        STATUS_INTERVIEW: 'yellow',
        STATUS_OFFER: 'green',
        STATUS_REJECTED: 'red',
        STATUS_WITHDRAWN: 'gray',
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED)
    job_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    resume_used = models.ForeignKey(
        Resume, null=True, blank=True, on_delete=models.SET_NULL, related_name='applications'
    )
    tailored_resume = models.ForeignKey(
        TailoredResume, null=True, blank=True, on_delete=models.SET_NULL, related_name='applications'
    )
    applied_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.role} at {self.company} ({self.status})"

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'gray')
