from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from .models import Resume, PortfolioTemplate, GeneratedPortfolio
from .forms import ResumeUploadForm, PortfolioTemplateForm
from .services import PortfolioGenerator, ContentGenerator, NetlifyDeployer
import os
from django.conf import settings


@login_required
def dashboard(request):
    # Get user's resumes
    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
    
    # Get recent portfolios
    recent_portfolios = GeneratedPortfolio.objects.filter(user=request.user).order_by('-created_at')[:3]
    
    # Get available templates
    templates = PortfolioTemplate.objects.filter(is_active=True)[:3]
    
    context = {
        'resumes': resumes,
        'recent_portfolios': recent_portfolios,
        'templates': templates,
    }
    return render(request, 'generator/dashboard.html', context)

# Resume Upload
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
    
    return render(request, 'generator/upload_resume.html', {'form': form})

# Resume Delete
@login_required
def delete_resume(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if request.method == 'POST':
        resume.file.delete()  # Delete the file from storage
        resume.delete()  # Delete the database record
        messages.success(request, 'Resume deleted successfully!')
        return redirect('generator:dashboard')
    return render(request, 'generator/confirm_delete.html', {'resume': resume})

# Portfolio Templates
@login_required
def portfolio_templates(request):
    templates = PortfolioTemplate.objects.filter(is_active=True)
    resumes = Resume.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'generator/portfolio_templates.html', {
        'templates': templates,
        'resumes': resumes
    })

# Portfolio Generation
@login_required
def generate_portfolio(request, template_id):
    if request.method != 'POST':
        return redirect('generator:portfolio_templates')
    
    template = get_object_or_404(PortfolioTemplate, id=template_id, is_active=True)
    resume_id = request.POST.get('resume_id')
    
    if not resume_id:
        messages.error(request, 'Please select a resume.')
        return redirect('generator:portfolio_templates')
    
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    
    try:
        generator = PortfolioGenerator(request.user, template, resume)
        portfolio = generator.generate_portfolio()
        messages.success(request, 'Portfolio generated successfully!')
        return redirect('generator:view_portfolio', portfolio_id=portfolio.id)
    except Exception as e:
        messages.error(request, f'Error generating portfolio: {str(e)}')
        return redirect('generator:portfolio_templates')

# Portfolio View
@login_required
def view_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    return render(request, 'generator/view_portfolio.html', {'portfolio': portfolio})

# Portfolio List
@login_required
def portfolio_list(request):
    portfolios = GeneratedPortfolio.objects.filter(user=request.user)
    return render(request, 'generator/portfolio_list.html', {'portfolios': portfolios})

# Portfolio Template Management (Admin Only)
@staff_member_required
def manage_templates(request):
    if request.method == 'POST':
        form = PortfolioTemplateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Template added successfully!')
            return redirect('generator:manage_templates')
    else:
        form = PortfolioTemplateForm()
    
    templates = PortfolioTemplate.objects.all()
    return render(request, 'generator/manage_templates.html', {
        'form': form,
        'templates': templates
    })

@login_required
def serve_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    
    # Construct the path to the index.html file
    portfolio_path = os.path.join(settings.MEDIA_ROOT, 'portfolios', f"{request.user.username}_{portfolio.template.name}")
    index_path = os.path.join(portfolio_path, 'index.html')
    
    try:
        # Read the index.html file
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Update relative paths to use the correct media URL
        content = content.replace('href="css/', f'href="{settings.MEDIA_URL}portfolios/{request.user.username}_{portfolio.template.name}/css/')
        content = content.replace('src="js/', f'src="{settings.MEDIA_URL}portfolios/{request.user.username}_{portfolio.template.name}/js/')
        content = content.replace('src="images/', f'src="{settings.MEDIA_URL}portfolios/{request.user.username}_{portfolio.template.name}/images/')
        
        # Serve the content with appropriate content type
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("Portfolio site not found. Please try generating the portfolio again.", status=404)
    except Exception as e:
        return HttpResponse(f"Error serving portfolio: {str(e)}", status=500)

@login_required
def delete_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Delete the portfolio folder
            portfolio_path = os.path.join('media', 'portfolios', f"{request.user.username}_{portfolio.template.name}")
            if os.path.exists(portfolio_path):
                import shutil
                shutil.rmtree(portfolio_path)
            
            # Delete the database record
            portfolio.delete()
            messages.success(request, 'Portfolio deleted successfully!')
            return redirect('generator:portfolio_list')
        except Exception as e:
            messages.error(request, f'Error deleting portfolio: {str(e)}')
            return redirect('generator:portfolio_list')
    
    return render(request, 'generator/confirm_delete_portfolio.html', {'portfolio': portfolio})

@login_required
def deploy_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(GeneratedPortfolio, id=portfolio_id, user=request.user)
    
    if request.method == 'POST':
        try:
            deployer = NetlifyDeployer(portfolio)
            site_url = deployer.deploy()
            messages.success(request, f'Portfolio successfully deployed to {site_url}')
        except Exception as e:
            messages.error(request, f'Failed to deploy portfolio: {str(e)}')
    
    return redirect('generator:view_portfolio', portfolio_id=portfolio.id)
