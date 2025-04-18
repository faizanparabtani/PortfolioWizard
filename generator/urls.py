from django.urls import path
from . import views

app_name = 'generator'

urlpatterns = [
    path('resumes/upload/', views.upload_resume, name='upload_resume'),
    path('resumes/', views.resume_list, name='resume_list'),
    path('resumes/<int:resume_id>/delete/', views.delete_resume, name='delete_resume'),
    
    # Portfolio URLs
    path('templates/', views.portfolio_templates, name='portfolio_templates'),
    path('generate/<int:template_id>/<int:resume_id>/', views.generate_portfolio, name='generate_portfolio'),
    path('portfolios/', views.portfolio_list, name='portfolio_list'),
    path('portfolios/<int:portfolio_id>/', views.view_portfolio, name='view_portfolio'),
    path('manage-templates/', views.manage_templates, name='manage_templates'),
] 