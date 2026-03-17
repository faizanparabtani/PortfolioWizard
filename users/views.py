import logging
import threading
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render

from .forms import UserLoginForm, UserRegisterForm

logger = logging.getLogger(__name__)


def _consume_guest_session(request, user):
    """
    After login or registration, check whether the guest stashed a resume and
    template in the session.  If so, create a Resume, kick off portfolio
    generation in a background thread, clear the session keys, and return the
    GeneratedPortfolio so the view can redirect to the loading page.
    Returns None when there is nothing to process.
    """
    guest_resume_path = request.session.get('guest_resume_path')
    guest_resume_name = request.session.get('guest_resume_name')
    guest_template_id = request.session.get('guest_template_id')

    if not (guest_resume_path and guest_template_id):
        return None

    try:
        from django.core.files import File as DjangoFile
        from generator.models import GeneratedPortfolio, PortfolioTemplate, Resume
        from generator.services.portfolio_generator import PortfolioGenerator

        resume_path = Path(guest_resume_path)
        if not resume_path.exists():
            return None

        template = PortfolioTemplate.objects.filter(
            id=guest_template_id, is_active=True
        ).first()
        if not template:
            return None

        # Persist the uploaded PDF as a proper Resume record
        resume = Resume(user=user, name=guest_resume_name or 'Uploaded Resume')
        with open(resume_path, 'rb') as f:
            resume.file.save(resume_path.name, DjangoFile(f), save=True)

        # Remove the temp file now that it is saved
        try:
            resume_path.unlink()
        except Exception:
            pass

        # Create the portfolio record (status=processing)
        portfolio = GeneratedPortfolio.objects.create(
            user=user,
            template=template,
            resume=resume,
            title=f"{user.username}'s Portfolio",
            description='Portfolio generation in progress...',
            portfolio_folder=f'portfolios/{user.username}_{template.name}/',
        )

        def _generate():
            try:
                gen = PortfolioGenerator(user, template, resume, portfolio)
                gen.generate_portfolio()
                portfolio.status = GeneratedPortfolio.STATUS_COMPLETED
                portfolio.status_message = 'Portfolio generated successfully!'
                portfolio.save(update_fields=['status', 'status_message'])
            except Exception:
                logger.exception(
                    'Guest portfolio generation failed for portfolio %s', portfolio.id
                )
                portfolio.status = GeneratedPortfolio.STATUS_ERROR
                portfolio.status_message = 'Generation failed. Please try again.'
                portfolio.save(update_fields=['status', 'status_message'])

        threading.Thread(target=_generate, daemon=True).start()

        # Clean up guest session keys
        for key in ('guest_resume_path', 'guest_resume_name', 'guest_template_id'):
            request.session.pop(key, None)
        request.session.modified = True

        return portfolio

    except Exception:
        logger.exception('Failed to process guest session data for user %s', user.pk)
        return None


def register(request):
    if request.user.is_authenticated:
        return redirect('generator:dashboard')
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            portfolio = _consume_guest_session(request, user)
            messages.success(request, 'Account created successfully!')
            if portfolio:
                return render(request, 'theme/loading.html', {'portfolio_id': portfolio.id})
            return redirect('generator:dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'theme/register.html', {
        'form': form,
        'guest_resume_name': request.session.get('guest_resume_name'),
    })


def user_login(request):
    if request.user.is_authenticated:
        return redirect('generator:dashboard')
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user is not None:
                login(request, user)
                portfolio = _consume_guest_session(request, user)
                messages.success(request, 'Logged in successfully!')
                if portfolio:
                    return render(request, 'theme/loading.html', {'portfolio_id': portfolio.id})
                return redirect('generator:dashboard')
    else:
        form = UserLoginForm()
    return render(request, 'theme/login.html', {
        'form': form,
        'guest_resume_name': request.session.get('guest_resume_name'),
    })
