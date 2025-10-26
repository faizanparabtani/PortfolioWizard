from django import forms
from .models import Resume, PortfolioTemplate

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file', 'name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resume Name'}),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }

class PortfolioTemplateForm(forms.ModelForm):
    class Meta:
        model = PortfolioTemplate
        fields = ['name', 'description', 'template_folder', 'thumbnail', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'template_folder': forms.TextInput(attrs={'placeholder': 'e.g., templates/modern_portfolio'}),
        } 