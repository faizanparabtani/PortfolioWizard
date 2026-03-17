import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ResumeUploadForm, TailorResumeForm
from ..models import Resume, TailoredResume
from ..services.resume_parser import ResumeParser
from ..services.resume_tailor import ResumeTailor

logger = logging.getLogger(__name__)


@login_required
def upload_resume(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()
            messages.success(request, 'Resume uploaded successfully!')
            return redirect('generator:dashboard')
    else:
        form = ResumeUploadForm()
    return render(request, 'theme/upload_resume.html', {'form': form})


@login_required
def delete_resume(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if request.method == 'POST':
        resume.file.delete()
        resume.delete()
        messages.success(request, 'Resume deleted successfully!')
        return redirect('generator:dashboard')
    return render(request, 'theme/confirm_delete.html', {'resume': resume})


@login_required
def tailor_resume(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if request.method == 'POST':
        form = TailorResumeForm(request.POST)
        if form.is_valid():
            try:
                resume_text = ResumeParser(resume.file.path).extract_text()
                tailor = ResumeTailor(resume_text, form.cleaned_data['job_description'])
                result = tailor.tailor()
                tailored = TailoredResume.objects.create(
                    user=request.user,
                    resume=resume,
                    company_name=form.cleaned_data['company_name'],
                    role_title=form.cleaned_data['role_title'],
                    job_description=form.cleaned_data['job_description'],
                    tailored_content=result,
                )
                return redirect('generator:tailored_resume_detail', pk=tailored.pk)
            except Exception:
                logger.exception('Resume tailoring failed for resume %s', resume_id)
                messages.error(request, 'Tailoring failed. Please try again.')
    else:
        form = TailorResumeForm()
    return render(request, 'theme/tailor_resume.html', {'form': form, 'resume': resume})


@login_required
def tailored_resume_list(request):
    tailored = TailoredResume.objects.filter(user=request.user).select_related('resume')
    return render(request, 'theme/tailored_resume_list.html', {'tailored_resumes': tailored})


@login_required
def tailored_resume_detail(request, pk):
    tailored = get_object_or_404(TailoredResume, pk=pk, user=request.user)
    return render(request, 'theme/tailored_resume_detail.html', {
        'tailored': tailored,
        'content': tailored.tailored_content,
    })


@login_required
def delete_tailored_resume(request, pk):
    tailored = get_object_or_404(TailoredResume, pk=pk, user=request.user)
    if request.method == 'POST':
        tailored.delete()
        messages.success(request, 'Tailored resume deleted.')
    return redirect('generator:tailored_resume_list')
