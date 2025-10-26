from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    # Dashboard and main navigation
    path('', views.landing, name='landing'),
    path('dashboard', views.dashboard, name='dashboard'),
    
    # Resume management
    path('resumes/upload/', views.upload_resume, name='upload_resume'),
    path('resumes/<int:resume_id>/delete/', views.delete_resume, name='delete_resume'),
    
    # Portfolio management
    path('templates/', views.portfolio_templates, name='portfolio_templates'),
    path('generate/<int:template_id>/', views.generate_portfolio, name='generate_portfolio'),
    path('check-status/<int:portfolio_id>/', views.check_generation_status, name='check_generation_status'),
    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/<int:portfolio_id>/', views.view_portfolio, name='view_portfolio'),
    path('portfolios/<int:portfolio_id>/view/', views.serve_portfolio, name='serve_portfolio'),
    path('portfolios/<int:portfolio_id>/delete/', views.delete_portfolio, name='delete_portfolio'),
    path('portfolios/<int:portfolio_id>/deploy/', views.deploy_portfolio, name='deploy_portfolio'),
    path('manage-templates/', views.manage_templates, name='manage_templates'),
    path('portfolio/<int:portfolio_id>/edit/', views.edit_portfolio, name='edit_portfolio'),
] 