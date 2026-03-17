import logging
import uuid as uuid_module
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from ..models import PortfolioTemplate

logger = logging.getLogger(__name__)


def guest_upload(request):
    """Accept a PDF from the landing-page drop zone, stash it in session."""
    if request.method != 'POST':
        return redirect('generator:landing')

    file = request.FILES.get('resume')
    if not file:
        messages.error(request, 'Please select a PDF file.')
        return redirect('generator:landing')

    if not file.name.lower().endswith('.pdf'):
        messages.error(request, 'Only PDF files are accepted.')
        return redirect('generator:landing')

    if file.size > 5 * 1024 * 1024:
        messages.error(request, 'File must be under 5 MB.')
        return redirect('generator:landing')

    tmp_dir = Path(settings.MEDIA_ROOT) / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    filename = f"guest_{uuid_module.uuid4().hex}.pdf"
    tmp_path = tmp_dir / filename

    with open(tmp_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)

    request.session['guest_resume_path'] = str(tmp_path)
    request.session['guest_resume_name'] = file.name
    request.session.modified = True

    return redirect('generator:portfolio_templates')


def guest_select_template(request, template_id):
    """Store chosen template in session, send guest to register."""
    template = get_object_or_404(PortfolioTemplate, id=template_id, is_active=True)
    request.session['guest_template_id'] = template_id
    request.session.modified = True
    messages.info(
        request,
        f'Almost there! Create a free account to generate your "{template.name}" portfolio.',
    )
    return redirect('users:register')
