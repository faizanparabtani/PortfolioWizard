from .dashboard import dashboard, landing
from .guest import guest_select_template, guest_upload
from .jobs import application_create, application_delete, application_list, application_update
from .portfolio import (
    check_generation_status,
    delete_portfolio,
    edit_portfolio,
    generate_portfolio,
    manage_templates,
    portfolio_list,
    portfolio_templates,
    public_portfolio,
    serve_portfolio,
    view_portfolio,
)
from .resume import (
    delete_resume,
    delete_tailored_resume,
    tailor_resume,
    tailored_resume_detail,
    tailored_resume_list,
    upload_resume,
)

__all__ = [
    'landing', 'dashboard',
    'guest_upload', 'guest_select_template',
    'upload_resume', 'delete_resume',
    'tailor_resume', 'tailored_resume_list', 'tailored_resume_detail', 'delete_tailored_resume',
    'portfolio_templates', 'generate_portfolio', 'check_generation_status',
    'view_portfolio', 'portfolio_list', 'serve_portfolio', 'delete_portfolio',
    'edit_portfolio', 'public_portfolio', 'manage_templates',
    'application_list', 'application_create', 'application_update', 'application_delete',
]
