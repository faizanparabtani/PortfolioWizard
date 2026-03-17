import logging
import shutil
import threading
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import PortfolioTemplateForm
from ..models import GeneratedPortfolio, PortfolioTemplate, PortfolioView, Resume
from ..services.portfolio_generator import PortfolioGenerator
from ..utils import sanitize_html

logger = logging.getLogger(__name__)

_CSP = (
    "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com "
    "https://fonts.googleapis.com https://fonts.gstatic.com; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data:;"
)


def portfolio_templates(request):
    """Browse templates — accessible to guests and authenticated users."""
    templates = PortfolioTemplate.objects.filter(is_active=True)
    resumes = []
    selected_resume = None
    guest_resume_name = None

    if request.user.is_authenticated:
        resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
        selected_resume_id = request.GET.get('resume_id')
        if selected_resume_id:
            try:
                selected_resume = Resume.objects.get(id=selected_resume_id, user=request.user)
            except Resume.DoesNotExist:
                pass
    else:
        guest_resume_name = request.session.get('guest_resume_name')

    return render(request, 'theme/portfolio_templates.html', {
        'templates': templates,
        'resumes': resumes,
        'selected_resume': selected_resume,
        'guest_resume_name': guest_resume_name,
    })


@login_required
def generate_portfolio(request, template_id):
    if request.method != 'POST':
        return redirect('generator:portfolio_templates')

    template = get_object_or_404(PortfolioTemplate, id=template_id, is_active=True)
    resume_id = request.POST.get('resume_id')
    if not resume_id:
        messages.error(request, 'Please select a resume.')
        return redirect('generator:portfolio_templates')

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)

    portfolio = GeneratedPortfolio.objects.create(
        user=request.user,
        template=template,
        resume=resume,
        title=f"{request.user.username}'s Portfolio",
        description='Portfolio generation in progress...',
        portfolio_folder=f'portfolios/{request.user.username}_{template.name}/',
    )

    def _generate():
        try:
            generator = PortfolioGenerator(request.user, template, resume, portfolio)
            generator.generate_portfolio()
            portfolio.status = GeneratedPortfolio.STATUS_COMPLETED
            portfolio.status_message = 'Portfolio generated successfully!'
            portfolio.save(update_fields=['status', 'status_message'])
        except Exception:
            logger.exception('Portfolio generation failed for portfolio %s', portfolio.id)
            portfolio.status = GeneratedPortfolio.STATUS_ERROR
            portfolio.status_message = 'Generation failed. Please try again.'
            portfolio.save(update_fields=['status', 'status_message'])

    threading.Thread(target=_generate, daemon=True).start()
    return render(request, 'theme/loading.html', {'portfolio_id': portfolio.id})


@login_required
def check_generation_status(request, portfolio_id):
    try:
        portfolio = GeneratedPortfolio.objects.get(id=portfolio_id, user=request.user)
        return JsonResponse({'status': portfolio.status, 'message': portfolio.status_message})
    except GeneratedPortfolio.DoesNotExist:
        return JsonResponse({'status': 'not_found', 'message': 'Portfolio not found'})


@login_required
def view_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(
        GeneratedPortfolio.objects.select_related('template', 'resume'),
        id=portfolio_id,
        user=request.user,
    )
    return render(request, 'theme/view_portfolio.html', {'portfolio': portfolio})


@login_required
def portfolio_list(request):
    qs = (
        GeneratedPortfolio.objects
        .filter(user=request.user)
        .select_related('template', 'resume')
        .order_by('-created_at')
    )
    paginator = Paginator(qs, 10)
    portfolios = paginator.get_page(request.GET.get('page'))
    return render(request, 'theme/portfolio_list.html', {'portfolios': portfolios})


@login_required
def serve_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    html_content = portfolio.generated_content.get('html_content', '')
    response = HttpResponse(html_content, content_type='text/html')
    response['X-Frame-Options'] = 'SAMEORIGIN'
    response['Content-Security-Policy'] = _CSP
    return response


@login_required
def delete_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(
        GeneratedPortfolio.objects.select_related('template'),
        id=portfolio_id,
        user=request.user,
    )
    if request.method == 'POST':
        try:
            media_root = Path(settings.MEDIA_ROOT).resolve()
            portfolio_path = (media_root / portfolio.portfolio_folder).resolve()
            if portfolio_path.is_dir() and portfolio_path.is_relative_to(media_root):
                shutil.rmtree(portfolio_path)
            portfolio.delete()
            messages.success(request, 'Portfolio deleted successfully!')
        except Exception:
            logger.exception('Failed to delete portfolio %s', portfolio_id)
            messages.error(request, 'Error deleting portfolio. Please try again.')
    return redirect('generator:portfolio_list')


@login_required
def edit_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    if request.method == 'POST':
        edited_content = request.POST.get('html_content', '')
        if edited_content:
            portfolio.generated_content['html_content'] = sanitize_html(edited_content)
            portfolio.save(update_fields=['generated_content'])
            messages.success(request, 'Portfolio updated successfully!')
            return redirect('generator:view_portfolio', portfolio_id=portfolio.id)
    return render(request, 'theme/edit_portfolio.html', {
        'portfolio': portfolio,
        'html_content': portfolio.generated_content.get('html_content', ''),
    })


def public_portfolio(request, slug):
    """Publicly accessible portfolio view — no login required. Logs each view."""
    portfolio = get_object_or_404(GeneratedPortfolio, public_slug=slug)
    html_content = portfolio.generated_content.get('html_content', '')
    if not html_content:
        raise Http404

    PortfolioView.objects.create(
        portfolio=portfolio,
        referrer=request.META.get('HTTP_REFERER', '')[:500],
        ip_hash=PortfolioView.get_ip_hash(request),
    )

    response = HttpResponse(html_content, content_type='text/html')
    response['X-Frame-Options'] = 'SAMEORIGIN'
    response['Content-Security-Policy'] = _CSP
    return response


@staff_member_required
def manage_templates(request):
    if request.method == 'POST':
        form = PortfolioTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template added successfully!')
            return redirect('generator:manage_templates')
    else:
        form = PortfolioTemplateForm()
    templates = PortfolioTemplate.objects.all()
    return render(request, 'theme/manage_templates.html', {
        'form': form,
        'templates': templates,
    })
