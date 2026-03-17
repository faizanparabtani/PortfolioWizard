from django.contrib import admin
from .models import GeneratedPortfolio, JobApplication, PortfolioTemplate, PortfolioView, Resume, TailoredResume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'uploaded_at')
    list_filter = ('uploaded_at',)
    readonly_fields = ('user', 'uploaded_at')
    search_fields = ('user__username', 'name')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(PortfolioTemplate)
class PortfolioTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(GeneratedPortfolio)
class GeneratedPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'template', 'status', 'is_published', 'created_at')
    list_filter = ('status', 'is_published', 'created_at')
    search_fields = ('user__username', 'title')
    readonly_fields = ('user', 'created_at', 'generated_content', 'status', 'status_message', 'public_slug')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'template', 'resume')


@admin.register(PortfolioView)
class PortfolioViewAdmin(admin.ModelAdmin):
    list_display = ('portfolio', 'viewed_at', 'referrer')
    readonly_fields = ('portfolio', 'viewed_at', 'referrer', 'ip_hash')


@admin.register(TailoredResume)
class TailoredResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_title', 'company_name', 'created_at')
    readonly_fields = ('user', 'resume', 'created_at', 'tailored_content')
    search_fields = ('user__username', 'role_title', 'company_name')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role', 'status', 'applied_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'company', 'role')
