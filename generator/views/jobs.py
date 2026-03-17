import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import JobApplicationForm
from ..models import JobApplication

logger = logging.getLogger(__name__)


@login_required
def application_list(request):
    status_filter = request.GET.get('status', '')
    qs = JobApplication.objects.filter(user=request.user).select_related('resume_used', 'tailored_resume')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'theme/application_list.html', {
        'applications': qs,
        'status_filter': status_filter,
        'status_choices': JobApplication.STATUS_CHOICES,
    })


@login_required
def application_create(request):
    if request.method == 'POST':
        form = JobApplicationForm(request.user, request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.save()
            messages.success(request, f'Application to {app.company} added.')
            return redirect('generator:application_list')
    else:
        form = JobApplicationForm(request.user)
    return render(request, 'theme/application_form.html', {'form': form, 'action': 'Add'})


@login_required
def application_update(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == 'POST':
        form = JobApplicationForm(request.user, request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, 'Application updated.')
            return redirect('generator:application_list')
    else:
        form = JobApplicationForm(request.user, instance=application)
    return render(request, 'theme/application_form.html', {'form': form, 'action': 'Edit', 'application': application})


@login_required
def application_delete(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Application removed.')
    return redirect('generator:application_list')
