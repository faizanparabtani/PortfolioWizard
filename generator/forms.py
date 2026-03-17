from django import forms
from django.core.validators import FileExtensionValidator

from .models import JobApplication, PortfolioTemplate, Resume

MAX_RESUME_SIZE_MB = 5


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file', 'name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Resume Name'}),
            'file': forms.FileInput(attrs={'accept': '.pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].validators.append(
            FileExtensionValidator(allowed_extensions=['pdf'])
        )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and file.size > MAX_RESUME_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f'File size must not exceed {MAX_RESUME_SIZE_MB} MB.')
        return file


class PortfolioTemplateForm(forms.ModelForm):
    class Meta:
        model = PortfolioTemplate
        fields = ['name', 'description', 'template_folder', 'thumbnail', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'template_folder': forms.TextInput(
                attrs={'placeholder': 'e.g., generator/templates/portfolios/modern'}
            ),
        }


class TailorResumeForm(forms.Form):
    role_title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Senior Django Developer'}),
    )
    company_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Stripe'}),
    )
    job_description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 12,
            'placeholder': 'Paste the full job description here...',
        }),
    )


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['company', 'role', 'status', 'job_url', 'applied_at', 'resume_used', 'tailored_resume', 'notes']
        widgets = {
            'company':    forms.TextInput(attrs={'placeholder': 'Company name'}),
            'role':       forms.TextInput(attrs={'placeholder': 'Role / job title'}),
            'job_url':    forms.URLInput(attrs={'placeholder': 'https://...'}),
            'applied_at': forms.DateInput(attrs={'type': 'date'}),
            'notes':      forms.Textarea(attrs={'rows': 4, 'placeholder': 'Interview notes, contacts, deadlines...'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resume_used'].queryset = Resume.objects.filter(user=user)
        self.fields['resume_used'].required = False
        self.fields['tailored_resume'].queryset = user.tailoredresume_set.all()
        self.fields['tailored_resume'].required = False
