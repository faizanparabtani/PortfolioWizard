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
    def __init__(self, resume_text):
        self.resume_text = resume_text
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            logger.error("OpenAI API key is missing")
            raise ValueError("OpenAI API key is required")
        
        # Configure OpenAI client
        openai.api_key = self.api_key
        self.model = "gpt-3.5-turbo"
        self.max_retries = 3
        self.initial_delay = 2

    def generate_content(self):
        """Generate portfolio content using OpenAI API"""
        try:
            logger.info("Starting content generation")
            return self._attempt_generation()
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            return self._create_response(self._get_default_sections())

    def _attempt_generation(self):
        """Generate content with OpenAI API"""
        try:
            # Create prompt
            prompt = self._get_simplified_prompt()
            logger.info("Prompt created successfully")
            
            # Make API call with retry logic
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"API Call Attempt {attempt + 1}/{self.max_retries}")
                    
                    # Split the prompt if it's too long
                    if len(prompt) > 4000:  # OpenAI's token limit is roughly 4000 tokens
                        prompt = self._truncate_prompt(prompt)
                    
                    response = openai.ChatCompletion.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant who rewrites resume content for a personal portfolio website. The tone should be concise, human, and engaging."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=2000,  # Increased from 1000
                        top_p=0.9,
                        frequency_penalty=0.5,
                        presence_penalty=0.5
                    )
                    
                    logger.info("API call successful")
                    
                    # Parse the response
                    if response and 'choices' in response and response['choices']:
                        content = response['choices'][0]['message']['content']
                        logger.info("Successfully received content from API")
                        sections = self._parse_content(content)
                        return self._create_response(sections)
                    
                except openai.error.RateLimitError as e:
                    logger.warning(f"Rate limit exceeded: {str(e)}")
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(f"Waiting {delay} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Rate limit exceeded after all retries")
                        raise
                        
                except openai.error.APIError as e:
                    logger.error(f"OpenAI API error: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
            
            raise Exception("All retry attempts failed")
            
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}")
            raise

    def _truncate_prompt(self, prompt):
        """Truncate the prompt if it's too long"""
        # Keep the instructions and truncate the resume text
        instructions = prompt.split("Based on this resume text:")[0]
        resume_text = prompt.split("Based on this resume text:")[1]
        
        # Truncate resume text to roughly 3000 characters
        truncated_resume = resume_text[:3000] + "...\n\n[Content truncated for length]"
        
        return f"{instructions}Based on this resume text:\n{truncated_resume}"

    def _get_simplified_prompt(self):
        """Create a simplified prompt for content generation"""
        return f"""Based on this resume text:
                {self.resume_text}

                Refine the content of the resume to be used in a personal portfolio website for the user,
                the content should ensure that all the information is present and relevant to the user.
                Some of the sections are optional and can be omitted if the user doesn't have any information for them,
                but the user should have the following sections:

                1. Information about the user
                2. About Me: A brief professional summary (2-3 sentences)
                3. Experience: Highlight roles with key achievements (Main portion of the content)
                4. Skills: List skills and expertise
                5. Projects: Describe 2-3 significant projects

                Keep each section concise and professional and suitable for a portfolio website."""

    def _parse_content(self, content: str) -> dict:
        """Parse the generated content into sections"""
        sections = {
            'about': '',
            'skills': [],
            'experience': '',
            'projects': ''
        }
        
        # Split content into sections
        current_section = None
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if 'About Me' in line or 'About:' in line:
                current_section = 'about'
            elif 'Skills' in line or 'Skills:' in line:
                current_section = 'skills'
            elif 'Experience' in line or 'Experience:' in line:
                current_section = 'experience'
            elif 'Projects' in line or 'Projects:' in line:
                current_section = 'projects'
            elif current_section:
                if current_section == 'skills':
                    # Extract skills from the line
                    skills = [s.strip() for s in line.split(',') if s.strip()]
                    sections['skills'].extend(skills)
                else:
                    sections[current_section] += line + '\n'
        
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
            'model_used': self.model
        }

    def _create_html_template(self, sections):
        """Create the complete HTML template with all sections"""
        return f"""
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
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <div class="container">
                    <a class="navbar-brand" href="#">My Portfolio</a>
                </div>
            </nav>
            
            <main class="container py-5">
                <section id="about" class="mb-5">
                    <h2 class="mb-4">About Me</h2>
                    <div class="section-content">{sections['about']}</div>
                </section>
                
                <section id="skills" class="mb-5">
                    <h2 class="mb-4">Skills & Expertise</h2>
                    <div class="row">
                        {' '.join(f'<div class="col-md-4 mb-3"><div class="skill-item p-2 border rounded">{skill}</div></div>' for skill in sections['skills'])}
                    </div>
                </section>
                
                <section id="experience" class="mb-5">
                    <h2 class="mb-4">Professional Experience</h2>
                    <div class="section-content">{sections['experience']}</div>
                </section>
                
                <section id="projects" class="mb-5">
                    <h2 class="mb-4">Projects</h2>
                    <div class="section-content">{sections['projects']}</div>
                </section>
            </main>
            
            <footer class="bg-dark text-white py-4 mt-5">
                <div class="container text-center">
                    <p>&copy; 2024 My Portfolio. All rights reserved.</p>
                </div>
            </footer>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        """

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
            content_generator = ContentGenerator(resume_text)
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
            raise ValueError("NETLIFY_TOKEN is required for deployment")
        
        self.site_name = f"{portfolio.user.username}-site"
        self.portfolio_path = os.path.join(settings.MEDIA_ROOT, 'portfolios', f"{portfolio.user.username}_{portfolio.template.name}")
        self.headers = {
            "Authorization": f"Bearer {self.netlify_token}",
            "Content-Type": "application/json"
        }

    def deploy(self):
        """Deploy the portfolio to Netlify"""
        try:
            logger.info("Starting portfolio deployment...")
            
            # Get or create the Netlify site
            logger.info("Getting or creating Netlify site...")
            site_id = self._get_or_create_site()
            logger.info(f"Got site ID: {site_id}")
            
            # Deploy the index.html file directly
            logger.info("Deploying index.html...")
            index_path = os.path.join(self.portfolio_path, 'index.html')
            deploy_response = self._deploy_file(site_id, index_path)
            logger.info("Deployment started successfully")
            
            # Update the portfolio status
            self.portfolio.is_published = True
            self.portfolio.save()
            logger.info("Updated portfolio status to published")
            
            # Return the site URL
            site_url = f"https://{self.site_name}.netlify.app"
            logger.info(f"Deployment complete. Site URL: {site_url}")
            return site_url
            
        except Exception as e:
            logger.error(f"Failed to deploy portfolio: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            raise

    def _get_or_create_site(self):
        """Get existing site or create a new one"""
        try:
            logger.info("Listing Netlify sites...")
            # Get all sites
            response = requests.get(
                "https://api.netlify.com/api/v1/sites",
                headers=self.headers
            )
            response.raise_for_status()
            sites = response.json()
            logger.info(f"Found {len(sites)} sites")
            
            # Try to find existing site
            for site in sites:
                logger.info(f"Checking site: {site}")
                if site.get('name') == self.site_name:
                    logger.info(f"Found existing site with ID: {site.get('id')}")
                    return site.get('id')
            
            # Create new site if not found
            logger.info("Creating new site...")
            site_data = {
                'name': self.site_name,
                'custom_domain': None,
                'password': None,
                'ssl': True,
                'force_ssl': True
            }
            
            response = requests.post(
                "https://api.netlify.com/api/v1/sites",
                headers=self.headers,
                json=site_data
            )
            response.raise_for_status()
            new_site = response.json()
            logger.info(f"Created new site: {new_site}")
            return new_site.get('id')
            
        except Exception as e:
            logger.error(f"Error getting/creating Netlify site: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error args: {e.args}")
            raise

    def _deploy_file(self, site_id, file_path):
        """Deploy a single file to Netlify"""
        try:
            logger.info(f"Deploying file: {file_path}")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Prepare the deploy data with the file content
            deploy_data = {
                'files': {
                    'index.html': file_content
                }
            }
            
            # Deploy the file
            response = requests.post(
                f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
                headers={
                    "Authorization": f"Bearer {self.netlify_token}",
                    "Content-Type": "application/json"
                },
                json=deploy_data
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error deploying file: {str(e)}")
            raise 