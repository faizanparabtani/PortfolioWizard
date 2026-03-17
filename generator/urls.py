from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    # Dashboard and main navigation
    path('', views.landing, name='landing'),
    path('dashboard', views.dashboard, name='dashboard'),

    # Guest flow (no auth required)
    path('guest-upload/', views.guest_upload, name='guest_upload'),
    path('guest-select/<int:template_id>/', views.guest_select_template, name='guest_select_template'),

    # Resume management
    path('resumes/upload/', views.upload_resume, name='upload_resume'),
    path('resumes/<int:resume_id>/delete/', views.delete_resume, name='delete_resume'),

    # Resume tailoring
    path('resumes/<int:resume_id>/tailor/', views.tailor_resume, name='tailor_resume'),
    path('tailored-resumes/', views.tailored_resume_list, name='tailored_resume_list'),
    path('tailored-resumes/<int:pk>/', views.tailored_resume_detail, name='tailored_resume_detail'),
    path('tailored-resumes/<int:pk>/delete/', views.delete_tailored_resume, name='delete_tailored_resume'),

    # Portfolio management
    path('templates/', views.portfolio_templates, name='portfolio_templates'),
    path('generate/<int:template_id>/', views.generate_portfolio, name='generate_portfolio'),
    path('check-status/<int:portfolio_id>/', views.check_generation_status, name='check_generation_status'),
    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/<int:portfolio_id>/', views.view_portfolio, name='view_portfolio'),
    path('portfolios/<int:portfolio_id>/view/', views.serve_portfolio, name='serve_portfolio'),
    path('portfolios/<int:portfolio_id>/delete/', views.delete_portfolio, name='delete_portfolio'),
    path('portfolio/<int:portfolio_id>/edit/', views.edit_portfolio, name='edit_portfolio'),
    path('manage-templates/', views.manage_templates, name='manage_templates'),

    # Public shareable portfolio — no login required
    path('p/<uuid:slug>/', views.public_portfolio, name='public_portfolio'),

    # Job application tracker
    path('applications/', views.application_list, name='application_list'),
    path('applications/add/', views.application_create, name='application_create'),
    path('applications/<int:pk>/edit/', views.application_update, name='application_update'),
    path('applications/<int:pk>/delete/', views.application_delete, name='application_delete'),
]
