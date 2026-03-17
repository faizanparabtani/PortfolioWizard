import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import GeneratedPortfolio, JobApplication, Resume

logger = logging.getLogger(__name__)


def landing(request):
    return render(request, 'theme/landing.html')


@login_required
def dashboard(request):
    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
    recent_portfolios = (
        GeneratedPortfolio.objects
        .filter(user=request.user)
        .select_related('template', 'resume')
        .order_by('-created_at')[:3]
    )
    application_counts = {
        status: JobApplication.objects.filter(user=request.user, status=status).count()
        for status, _ in JobApplication.STATUS_CHOICES
    }

    has_resume = resumes.exists()
    latest_portfolio = recent_portfolios[0] if recent_portfolios else None
    has_portfolio = (
        latest_portfolio is not None
        and latest_portfolio.status == GeneratedPortfolio.STATUS_COMPLETED
    )
    total_applications = sum(application_counts.values())

    return render(request, 'theme/dashboard.html', {
        'resumes': resumes,
        'recent_portfolios': recent_portfolios,
        'application_counts': application_counts,
        'has_resume': has_resume,
        'latest_portfolio': latest_portfolio,
        'has_portfolio': has_portfolio,
        'total_applications': total_applications,
    })
