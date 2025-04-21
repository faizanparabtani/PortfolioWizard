import os
import json
import PyPDF2
import requests
import logging
import re
import time
import random
import openai
from django.conf import settings
from .models import Resume, GeneratedPortfolio
from bs4 import BeautifulSoup
from typing import Optional
import netlify
import shutil
import tempfile
import io
import zipfile
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)

class ResumeParser:
    def __init__(self, resume_file):
        self.resume_file = resume_file

    def extract_text(self):
        """Extract text from PDF resume"""
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(self.resume_file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
        return text

class ContentGenerator:
    def __init__(self, resume_text, user):
        self.resume_text = resume_text
        self.user = user
        self.model = genai.GenerativeModel('gemini-1.5-pro')  # Using the latest stable model
        self.logger = logging.getLogger(__name__)
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.error("Gemini API key is missing")
            raise ValueError("Gemini API key is required")
        
        # Configure Gemini client
        genai.configure(api_key=self.api_key)
        self.max_retries = 3
        self.initial_delay = 2

    def generate_content(self):
        """Generate portfolio content using Gemini API"""
        try:
            logger.info("Starting content generation with Gemini")
            
            # Set generation config
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            return self._attempt_generation(generation_config=generation_config)
            
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            return self._create_response(self._get_default_sections())

    def _attempt_generation(self, generation_config=None):
        """Generate content with Gemini API"""
        try:
            # Create prompt
            prompt = self._get_simplified_prompt()
            logger.info("Prompt created successfully")
            
            # Make API call with retry logic
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"API Call Attempt {attempt + 1}/{self.max_retries}")
                    
                    # Generate content with configuration
                    response = self.model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                    
                    if response and response.text:
                        logger.info("Successfully received content from API")
                        logger.info(f"Raw response: {response.text}")  # Log the raw response
                        sections = self._parse_content(response.text)
                        logger.info(f"Parsed sections: {sections}")  # Log the parsed sections
                        return self._create_response(sections)
                    else:
                        raise Exception("Empty response from Gemini API")
                    
                except Exception as e:
                    logger.error(f"Error in generation attempt {attempt + 1}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(f"Waiting {delay} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        raise
            
            raise Exception("All retry attempts failed")
            
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}")
            raise

    def _get_simplified_prompt(self):
        """Create a simplified prompt for content generation"""
        return f"""Analyze this resume and create portfolio content:

            {self.resume_text}

            Format your response EXACTLY as follows (keep the section headers exactly as shown):

            [ABOUT]
            A software engineer with X years of experience specializing in... (write 2-3 sentences based on the resume, in first person)

            [SKILLS]
            * Python
            * Django
            (list actual skills from resume, one per line with asterisk)

            [EXPERIENCE]
            * **Senior Developer at Tech Corp (2020-Present)**
            * Developed feature X that achieved Y
            * Led project Z with outcome W
            (list real experience with actual achievements)

            [PROJECTS]
            * **Project Name**
            * Built using actual technologies
            * Implemented real features
            (describe actual projects from resume)

            Note: Replace the example text with real information from the resume. Keep the exact formatting with asterisks and section headers."""

    def _parse_content(self, content: str) -> dict:
        """Parse the generated content into sections"""
        sections = {
            'about': '',
            'skills': [],
            'experience': '',
            'projects': ''
        }
        
        # Split into sections using markers
        parts = content.split('[')
        
        for part in parts:
            if not part.strip():
                continue
                
            # Identify section
            if part.startswith('ABOUT]'):
                section_content = part[6:].strip()  # Remove header
                sections['about'] = section_content
                
            elif part.startswith('SKILLS]'):
                skills_text = part[7:].strip()  # Remove header
                # Extract skills (lines starting with asterisk)
                skills = [line.strip('* ').strip() for line in skills_text.split('\n') 
                         if line.strip().startswith('*')]
                sections['skills'] = [skill for skill in skills if skill]
                
            elif part.startswith('EXPERIENCE]'):
                sections['experience'] = part[11:].strip()  # Remove header
                
            elif part.startswith('PROJECTS]'):
                sections['projects'] = part[9:].strip()  # Remove header
        
        # Clean up sections
        for key in ['experience', 'projects']:
            if sections[key]:
                # Remove any remaining instruction-like text
                lines = sections[key].split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip() and not any(marker in line.lower() for marker in ['example:', 'note:', 'replace']):
                        cleaned_lines.append(line)
                sections[key] = '\n'.join(cleaned_lines)
        
        # Clean up about section
        if sections['about']:
            # Remove any instruction-like text
            lines = sections['about'].split('\n')
            cleaned_lines = [line for line in lines 
                           if line.strip() and not any(marker in line.lower() 
                           for marker in ['example:', 'note:', 'replace'])]
            sections['about'] = ' '.join(cleaned_lines)
        
        return sections

    def _get_default_sections(self):
        """Return default sections if content generation fails"""
        return {
            'about': 'Professional summary not available.',
            'skills': ['Content generation failed. Please try again later.'],
            'experience': 'Work experience details not available.',
            'projects': 'Project information not available.'
        }

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter"""
        delay = self.initial_delay * (2 ** attempt)  # exponential backoff
        jitter = random.uniform(0, 0.1 * delay)  # add some randomness
        return delay + jitter

    def _create_response(self, sections):
        """Create the final response object"""
        html_content = self._create_html_template(sections)
        return {
            'html_content': html_content,
            'raw_content': sections,
            'model_used': 'gemini-1.5-pro'
        }

    def _create_html_template(self, sections):
        """Create the complete HTML template with all sections"""
        # Read the template file
        template_path = os.path.join(settings.BASE_DIR, 'generator', 'templates', 'portfolios', 'creative_professional', 'index.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Replace placeholders with actual content
        template = template.replace('{{ about.title }}', f"{self.user.get_full_name() or self.user.username}'s Portfolio")
        template = template.replace('{{ about.subtitle }}', sections['about'])
        template = template.replace('{{ about.description }}', sections['about'])
        
        # Replace social links section with empty string since we don't have social links
        template = template.replace('{% for link in about.social_links %}\n                <a href="{{ link.url }}" class="text-white me-3"><i class="{{ link.icon }} fa-2x"></i></a>\n                {% endfor %}', '')
        
        # Replace skills
        skills_html = ''.join([f'<span class="skill-badge">{skill}</span>' for skill in sections['skills']])
        template = template.replace('{% for skill in skills %}\n                <span class="skill-badge">{{ skill.name }}</span>\n                {% endfor %}', skills_html)
        
        # Replace experience
        experience_html = ''
        if sections['experience']:
            # Split the content into individual experiences
            experience_entries = []
            current_entry = []
            
            for line in sections['experience'].split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line starts a new experience (contains a date range in parentheses)
                if '(' in line and ')' in line and '-' in line:
                    if current_entry:
                        experience_entries.append('\n'.join(current_entry))
                        current_entry = []
                current_entry.append(line)
            
            # Add the last entry if exists
            if current_entry:
                experience_entries.append('\n'.join(current_entry))
            
            for entry in experience_entries:
                try:
                    lines = [line.strip() for line in entry.split('\n') if line.strip()]
                    if not lines:
                        continue
                    
                    # First line contains position and dates
                    header = lines[0].strip('* **').strip('**')
                    
                    # Try to extract dates if they exist
                    position = header
                    start_date = ""
                    end_date = ""
                    
                    if '(' in header and ')' in header:
                        try:
                            position, dates = header.split('(')
                            position = position.strip()
                            dates = dates.strip(')')
                            if '-' in dates:
                                start_date, end_date = dates.split('-')
                                start_date = start_date.strip()
                                end_date = end_date.strip()
                        except:
                            # If date parsing fails, just use the whole header as position
                            position = header
                    
                    # Remaining lines are bullet points
                    description = '\n'.join([f'<li>{line.strip("* ").strip()}</li>' for line in lines[1:]])
                    
                    experience_html += f"""
                    <div class="experience-item">
                        <div class="experience-header">
                            <div class="experience-company">{position}</div>
                            <div class="experience-position"></div>
                            <div class="experience-duration">{start_date} - {end_date}</div>
                        </div>
                        <div class="experience-description">
                            <ul>
                                {description}
                            </ul>
                        </div>
                    </div>
                    """
                except Exception as e:
                    logger.error(f"Error parsing experience entry: {str(e)}")
                    continue
        
        # Replace the entire experience section
        experience_section = f"""
            <h2 class="text-center mb-5">Professional Experience</h2>
            {experience_html}
        """
        template = template.replace('<!-- Experience Section -->\n    <section class="section bg-light">\n        <div class="container">\n            <h2 class="text-center mb-5">Professional Experience</h2>\n            {% for exp in experience %}\n            <div class="experience-item">\n                <div class="experience-header">\n                    <div class="experience-company">{{ exp.company }}</div>\n                    <div class="experience-position">{{ exp.position }}</div>\n                    <div class="experience-duration">{{ exp.start_date }} - {{ exp.end_date }}</div>\n                </div>\n                <div class="experience-description">\n                    {{ exp.description|linebreaks }}\n                </div>\n            </div>\n            {% endfor %}\n        </div>\n    </section>', experience_section)
        
        # Replace projects
        projects_html = ''
        if sections['projects']:
            # Split the content into individual projects
            project_entries = []
            current_entry = []
            
            for line in sections['projects'].split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line starts a new project (starts with **)
                if line.startswith('* **'):
                    if current_entry:
                        project_entries.append('\n'.join(current_entry))
                        current_entry = []
                current_entry.append(line)
            
            # Add the last entry if exists
            if current_entry:
                project_entries.append('\n'.join(current_entry))
            
            for entry in project_entries:
                try:
                    lines = [line.strip() for line in entry.split('\n') if line.strip()]
                    if not lines:
                        continue
                    
                    # First line is project title
                    title = lines[0].strip('* **').strip('**')
                    
                    # Remaining lines are bullet points
                    description = '\n'.join([f'<p>{line.strip("* ").strip()}</p>' for line in lines[1:]])
                    
                    projects_html += f"""
                    <div class="col-md-6">
                        <div class="project-card">
                            <img src="/static/images/default-project.jpg" class="card-img-top" alt="{title}">
                            <div class="card-body">
                                <h5 class="card-title">{title}</h5>
                                <p class="card-text">{description}</p>
                                <a href="#" class="btn btn-primary">Explore Project</a>
                            </div>
                        </div>
                    </div>
                    """
                except Exception as e:
                    logger.error(f"Error parsing project entry: {str(e)}")
                    continue
        
        # Replace the entire projects section
        projects_section = f"""
            <h2 class="text-center mb-5">Projects</h2>
            <div class="row">
                {projects_html}
            </div>
        """
        template = template.replace('<!-- Projects Section -->\n    <section class="section">\n        <div class="container">\n            <h2 class="text-center mb-5">Projects</h2>\n            <div class="row">\n                {% for project in projects %}\n                <div class="col-md-6">\n                    <div class="project-card">\n                        <img src="{{ project.image }}" class="card-img-top" alt="{{ project.title }}">\n                        <div class="card-body">\n                            <h5 class="card-title">{{ project.title }}</h5>\n                            <p class="card-text">{{ project.description|linebreaks }}</p>\n                            <a href="{{ project.url }}" class="btn btn-primary">Explore Project</a>\n                        </div>\n                    </div>\n                </div>\n                {% endfor %}\n            </div>\n        </div>\n    </section>', projects_section)
        
        # Replace current year
        template = template.replace('{{ current_year }}', str(datetime.now().year))
        
        return template

    def _clean_html(self, html_content: str) -> str:
        """Clean and format the generated HTML."""
        # Remove any potential script tags for security
        html_content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', html_content)
        
        # Ensure proper Bootstrap and other required resources are included
        if '<head>' not in html_content:
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Professional Portfolio</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            </head>
            <body>
            {html_content}
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            </body>
            </html>
            """
        
        return html_content

    def _extract_section(self, html_content: str, section_name: str) -> str:
        """Extract specific section content from the generated HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        section = soup.find('section', {'id': section_name}) or soup.find('div', {'id': section_name})
        return str(section) if section else ""

class PortfolioGenerator:
    def __init__(self, user, template, resume):
        self.user = user
        self.template = template
        self.resume = resume

    def generate_portfolio(self):
        """Generate a personalized portfolio"""
        try:
            # Parse resume
            parser = ResumeParser(self.resume.file)
            resume_text = parser.extract_text()

            # Generate content
            content_generator = ContentGenerator(resume_text, self.user)
            generated_content = content_generator.generate_content()

            # Create portfolio instance
            portfolio = GeneratedPortfolio.objects.create(
                user=self.user,
                template=self.template,
                resume=self.resume,
                title=f"{self.user.username}'s Portfolio",
                description="Generated portfolio based on resume",
                generated_content=generated_content,
                portfolio_folder=f"portfolios/{self.user.username}_{self.template.name}/"
            )

            # Generate portfolio files
            self._generate_portfolio_files(portfolio, generated_content)

            return portfolio
        except Exception as e:
            logger.error(f"Portfolio generation failed: {str(e)}")
            raise

    def _generate_portfolio_files(self, portfolio, content):
        """Generate the actual portfolio files"""
        try:
            template_path = os.path.join(settings.BASE_DIR, self.template.template_folder)
            portfolio_path = os.path.join(settings.MEDIA_ROOT, portfolio.portfolio_folder)

            # Create portfolio directory
            os.makedirs(portfolio_path, exist_ok=True)

            # Write the main index.html file
            index_path = os.path.join(portfolio_path, 'index.html')
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(content['html_content'])

            # Copy static assets from template
            self._copy_static_assets(template_path, portfolio_path)

        except Exception as e:
            logger.error(f"Failed to generate portfolio files: {str(e)}")
            raise

    def _copy_static_assets(self, template_path, portfolio_path):
        """Copy static assets (CSS, JS, images) from template to portfolio"""
        try:
            for root, dirs, files in os.walk(template_path):
                for file in files:
                    # Skip index.html as we're generating it
                    if file == 'index.html':
                        continue
                        
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, template_path)
                    dst_path = os.path.join(portfolio_path, rel_path)

                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    # Copy the file
                    with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                        dst.write(src.read())

        except Exception as e:
            logger.error(f"Failed to copy static assets: {str(e)}")
            raise

class NetlifyDeployer:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.netlify_token = settings.NETLIFY_TOKEN
        if not self.netlify_token:
            logger.error("NETLIFY_TOKEN is missing.")
            raise ValueError("NETLIFY_TOKEN is required for deployment")
        
        # Ensure site name is Netlify-compatible (lowercase, letters, numbers, hyphens)
        self.site_name = f"{portfolio.user.username}-site".lower().replace('_', '-')
        # Use MEDIA_ROOT setting correctly
        self.portfolio_path = os.path.join(settings.MEDIA_ROOT, 'portfolios', f"{portfolio.user.username}_{portfolio.template.name}")
        self.api_base_url = "https://api.netlify.com/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.netlify_token}"
        }
        logger.info(f"NetlifyDeployer initialized for path: {self.portfolio_path} and site name: {self.site_name}")

    def deploy(self):
        """Deploy the portfolio to Netlify by uploading a zip archive."""
        try:
            logger.info(f"Starting portfolio deployment for site: {self.site_name}")

            if not os.path.isdir(self.portfolio_path):
                logger.error(f"Portfolio directory not found: {self.portfolio_path}")
                raise FileNotFoundError(f"Portfolio directory not found: {self.portfolio_path}")
            
            logger.info("Getting or creating Netlify site...")
            site_id = self._get_or_create_site()
            if not site_id:
                 raise Exception("Could not get or create Netlify site.")
            logger.info(f"Using site ID: {site_id}")

            logger.info("Creating zip archive of the portfolio directory...")
            zip_buffer = self._zip_directory(self.portfolio_path)
            logger.info(f"Zip archive created in memory (Size: {zip_buffer.getbuffer().nbytes} bytes)")

            # Upload the zip file to start deployment
            logger.info("Uploading zip archive to Netlify...")
            deploy_headers = self.headers.copy()
            deploy_headers["Content-Type"] = "application/zip"
            
            upload_response = requests.post(
                f"{self.api_base_url}/sites/{site_id}/deploys",
                headers=deploy_headers,
                data=zip_buffer.getvalue()
            )
            upload_response.raise_for_status()
            deploy_details = upload_response.json()
            deploy_id = deploy_details.get('id')
            logger.info(f"Deployment initiated successfully. Deploy ID: {deploy_id}")

            # Wait for the deployment to complete
            logger.info("Waiting for deployment to finish processing...")
            final_state = self._wait_for_deployment(deploy_id)

            if final_state == 'ready':
                logger.info("Deployment successful and site is live.")
                self.portfolio.is_published = True
                self.portfolio.netlify_site_id = site_id
                self.portfolio.netlify_deploy_id = deploy_id
                self.portfolio.netlify_url = deploy_details.get('deploy_ssl_url') or deploy_details.get('deploy_url')
                self.portfolio.save()
                logger.info(f"Updated portfolio status to published. Site URL: {self.portfolio.netlify_url}")
                return self.portfolio.netlify_url
            else:
                logger.error(f"Netlify deployment failed or ended in state: {final_state}")
                raise Exception(f"Netlify deployment failed with state: {final_state}")

        except requests.exceptions.RequestException as req_e:
            logger.error(f"Netlify API request failed: {req_e}")
            if req_e.response is not None:
                 logger.error(f"Response status: {req_e.response.status_code}")
                 logger.error(f"Response body: {req_e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to deploy portfolio: {str(e)}", exc_info=True)
            raise

    def _get_or_create_site(self):
        """Get existing site ID or create a new one."""
        try:
            # List sites
            list_url = f"{self.api_base_url}/sites"
            logger.info(f"Listing sites via GET {list_url}")
            response = requests.get(list_url, headers=self.headers, params={'filter': 'all'})
            response.raise_for_status()
            sites = response.json()
            logger.info(f"Found {len(sites)} sites associated with the token.")

            # Check if site exists
            for site in sites:
                if site.get('name') == self.site_name:
                    logger.info(f"Found existing site '{self.site_name}' with ID: {site.get('id')}")
                    return site.get('id')

            # Create site if it doesn't exist
            logger.info(f"Site '{self.site_name}' not found. Creating new site...")
            create_url = f"{self.api_base_url}/sites"
            site_data = {'name': self.site_name}
            
            create_response = requests.post(create_url, headers=self.headers, json=site_data)
            
            if create_response.status_code == 422:
                 logger.error(f"Site name '{self.site_name}' might already be taken or invalid.")
                 time.sleep(2)
                 response = requests.get(list_url, headers=self.headers, params={'filter': 'all'})
                 response.raise_for_status()
                 sites = response.json()
                 for site in sites:
                     if site.get('name') == self.site_name:
                         logger.info(f"Found existing site '{self.site_name}' after creation conflict. ID: {site.get('id')}")
                         return site.get('id')
                 logger.error(f"Could not create or find site '{self.site_name}' after conflict.")
                 return None

            create_response.raise_for_status()
            new_site = create_response.json()
            logger.info(f"Created new site: {new_site.get('name')} with ID: {new_site.get('id')}")
            return new_site.get('id')

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting/creating Netlify site: {e}")
            if e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _get_or_create_site: {e}", exc_info=True)
            return None

    def _zip_directory(self, path):
        """Creates a zip archive of a directory in memory."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # First, add the index.html file at the root
            index_path = os.path.join(path, 'index.html')
            if os.path.exists(index_path):
                # Read the file content
                with open(index_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure proper HTML content type
                zf.writestr('index.html', content)
            
            # Then add all other files maintaining their directory structure
            for root, _, files in os.walk(path):
                for file in files:
                    if file == 'index.html':  # Skip index.html as we already added it
                        continue
                    file_path = os.path.join(root, file)
                    # Calculate the relative path from the portfolio directory
                    rel_path = os.path.relpath(file_path, path)
                    # Ensure paths use forward slashes for web compatibility
                    rel_path = rel_path.replace('\\', '/')
                    
                    # Read the file content
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    # Write the file content to the zip
                    zf.writestr(rel_path, content)
        
        buffer.seek(0)
        return buffer

    def _wait_for_deployment(self, deploy_id, timeout=300, interval=5):
        """Polls Netlify API to check deployment status."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                deploy_url = f"{self.api_base_url}/deploys/{deploy_id}"
                response = requests.get(deploy_url, headers=self.headers)
                response.raise_for_status()
                deploy_status = response.json()
                state = deploy_status.get('state')
                logger.info(f"Current deployment state: {state}")

                if state == 'ready':
                    return 'ready'
                elif state in ['error', 'failed']:
                    logger.error(f"Deployment failed. Status: {deploy_status}")
                    return state
                elif state == 'building' or state == 'uploading' or state == 'processing':
                    pass
                else:
                    logger.warning(f"Unknown deployment state encountered: {state}")

                time.sleep(interval)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error polling deployment status: {e}")
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Unexpected error during polling: {e}", exc_info=True)
                return "polling_error"

        logger.error(f"Deployment polling timed out after {timeout} seconds.")
        return 'timeout' 