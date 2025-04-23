import os
import logging
import re
import time
import random
from datetime import datetime
from django.conf import settings
import google.generativeai as genai
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self, resume_text, user, template):
        self.resume_text = resume_text
        self.user = user
        self.template = template
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.logger = logging.getLogger(__name__)
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            logger.error("Gemini API key is missing")
            raise ValueError("Gemini API key is required")
        
        # Configure Gemini client
        genai.configure(api_key=self.api_key)
        self.max_retries = 3
        self.initial_delay = 1.0  # Initial delay in seconds
        self.max_delay = 10.0  # Maximum delay in seconds

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
                        logger.info(f"Raw response: {response.text}")
                        sections = self._parse_content(response.text)
                        logger.info(f"Parsed sections: {sections}")
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
        return f"""Analyze this resume and create portfolio website content, elaborate where necessary and use impactful sentences:

            {self.resume_text}

            Format your response EXACTLY as follows (keep the section headers exactly as shown):

            [ABOUT]
            A software engineer with X years of experience specializing in... (write 2-3 impactful sentences based on the resume, in first person)

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
        # Read the template file based on the selected template
        template_name = self.template.name.lower().replace(' ', '_')
        template_path = os.path.join(settings.BASE_DIR, 'generator', 'templates', 'portfolios', template_name, 'index.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            logger.error(f"Template file not found at {template_path}")
            # Fallback to creative professional template
            template_path = os.path.join(settings.BASE_DIR, 'generator', 'templates', 'portfolios', 'creative_professional', 'index.html')
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        
        # Replace placeholders with actual content
        template = template.replace('{{ about.title }}', f"{self.user.get_full_name() or self.user.username}")
        template = template.replace('{{ about.description }}', sections['about'])
        
        # Replace skills section
        skills_html = ''.join([f'''
            <span class="skill-badge">{skill}</span>
        ''' for skill in sections['skills']])
        
        # Replace the entire skills section block
        template = template.replace(
            '{% for skill in skills %}\n                <span class="skill-badge">{{ skill.name }}</span>\n                {% endfor %}',
            skills_html
        )
        
        # Replace experience section
        experience_html = ''
        experience_text = sections['experience']
        if experience_text:
            # Split the content into individual experiences
            experience_entries = []
            current_entry = []
            
            for line in experience_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line starts a new experience (contains a date range in parentheses)
                if line.startswith('* **') and '(' in line and ')' in line and '-' in line:
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
                    position, dates = header.split('(')
                    position = position.strip()
                    start_date, end_date = dates.strip(')').split('-')
                    
                    # Extract company name from the first line if it exists
                    company = ''
                    if ' at ' in position:
                        position, company = position.split(' at ')
                        position = position.strip()
                        company = company.strip()
                    
                    # Remaining lines are bullet points
                    description = '\n'.join([f'<li>{line.strip("* ").strip()}</li>' for line in lines[1:]])
                    
                    experience_html += f'''
                    <div class="experience-item">
                        <div class="experience-header">
                            <div class="experience-company">{company}</div>
                            <div class="experience-position">{position}</div>
                            <div class="experience-duration">{start_date.strip()} - {end_date.strip()}</div>
                        </div>
                        <div class="experience-description">
                            <ul>
                                {description}
                            </ul>
                        </div>
                    </div>
                    '''
                except Exception as e:
                    logger.error(f"Error parsing experience entry: {e}")
                    continue
        
        # Replace the entire experience section block
        template = template.replace(
            '{% for exp in experience %}\n            <div class="experience-item">\n                <div class="experience-header">\n                    <div class="experience-company">{{ exp.company }}</div>\n                    <div class="experience-position">{{ exp.position }}</div>\n                    <div class="experience-duration">{{ exp.start_date }} - {{ exp.end_date }}</div>\n                </div>\n                <div class="experience-description">\n                    {{ exp.description|linebreaks }}\n                </div>\n            </div>\n            {% endfor %}',
            experience_html
        )
        
        # Replace projects section
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
                            <div class="card-body">
                                <h5 class="card-title">{title}</h5>
                                <div class="card-text">{description}</div>
                            </div>
                        </div>
                    </div>
                    """
                except Exception as e:
                    logger.error(f"Error parsing project entry: {str(e)}")
                    continue
        
        # Replace the entire projects section block
        template = template.replace(
            '{% for project in projects %}\n                <div class="col-md-6">\n                    <div class="project-card">\n                        <div class="card-body">\n                            <h5 class="card-title">{{ project.title }}</h5>\n                            <div class="card-text">{{ project.description|linebreaks }}</div>\n                        </div>\n                    </div>\n                </div>\n                {% endfor %}',
            projects_html
        )
        
        # Replace current year
        template = template.replace('{{ current_year }}', str(datetime.now().year))
        
        # Add CSS styles
        css = '''
        <style>
            .skill-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .skill-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            }
            
            .skill-title {
                color: #333;
                font-weight: 600;
                margin-bottom: 15px;
            }
            
            .skill-progress {
                height: 6px;
                background: #f0f0f0;
                border-radius: 3px;
                overflow: hidden;
            }
            
            .progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #6c5ce7, #a8a4e0);
                transition: width 1.5s ease-in-out;
            }
            
            .skill-item {
                opacity: 0;
                transform: translateY(20px);
                animation: fadeInUp 0.5s ease forwards;
            }
            
            @keyframes fadeInUp {
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            /* Stagger the animations */
            .skill-item:nth-child(1) { animation-delay: 0.1s; }
            .skill-item:nth-child(2) { animation-delay: 0.2s; }
            .skill-item:nth-child(3) { animation-delay: 0.3s; }
            .skill-item:nth-child(4) { animation-delay: 0.4s; }
            .skill-item:nth-child(5) { animation-delay: 0.5s; }
            .skill-item:nth-child(6) { animation-delay: 0.6s; }
        </style>
        '''
        template = template.replace('</head>', css + '</head>')
        
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