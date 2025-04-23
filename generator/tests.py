from django.test import TestCase
from .services.content_generator import ContentGenerator
from django.conf import settings
import logging
import google.generativeai as genai
import os
from django.contrib.auth import get_user_model
from .models import Resume, PortfolioTemplate, GeneratedPortfolio
from .services.portfolio_generator import PortfolioGenerator
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime

logger = logging.getLogger(__name__)

class TestGeminiAPI(TestCase):
    def test_list_available_models(self):
        """Test listing available Gemini models"""
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            models = list(genai.list_models())  # Convert generator to list
            logger.info("Available models:")
            for model in models:
                logger.info(f"Model: {model.name}")
                logger.info(f"Supported methods: {model.supported_generation_methods}")
            self.assertTrue(len(models) > 0, "No models found")
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            raise

    def test_gemini_api_connection(self):
        """Test if Gemini API is working correctly"""
        try:
            # Create test user and template
            user = get_user_model().objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            template = PortfolioTemplate.objects.create(
                name='Creative Professional',
                description='Test template',
                template_folder='portfolios/creative_professional',
                is_active=True
            )
            
            # Sample resume text for testing
            test_resume = """
            John Doe
            Software Engineer
            Experience:
            - Senior Developer at Tech Corp (2020-Present)
            - Junior Developer at Startup Inc (2018-2020)
            
            Skills:
            Python, Django, JavaScript, React
            
            Projects:
            - Portfolio Website: Built a personal portfolio using Django and React
            - E-commerce Platform: Developed a full-stack e-commerce solution
            """
            
            # Initialize the content generator
            generator = ContentGenerator(test_resume, user, template)
            
            # Attempt to generate content
            result = generator.generate_content()
            
            # Check if we got a valid response
            self.assertIsNotNone(result)
            self.assertIn('html_content', result)
            self.assertIn('raw_content', result)
            
            # Check if the content has the expected sections
            raw_content = result['raw_content']
            self.assertIn('about', raw_content)
            self.assertIn('skills', raw_content)
            self.assertIn('experience', raw_content)
            self.assertIn('projects', raw_content)
            
            logger.info("Gemini API test successful!")
            logger.info(f"Generated content: {result['raw_content']}")
            
        except Exception as e:
            logger.error(f"Gemini API test failed: {str(e)}")
            raise

class PortfolioGenerationTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test template
        self.template = PortfolioTemplate.objects.create(
            name='Creative Professional',
            description='Test template',
            template_folder='portfolios/creative_professional',
            is_active=True
        )
        
        # Create test resume with file
        resume_file = SimpleUploadedFile(
            "test_resume.txt",
            b"Test resume content",
            content_type="text/plain"
        )
        self.resume = Resume.objects.create(
            user=self.user,
            file=resume_file,
            name="Test Resume"
        )
        
        # Sample content from debug log
        self.sample_content = {
            'about': 'I am a software engineer specializing in developing robust and scalable web platforms and APIs using Python, Django, and Django REST Framework. I am passionate about leveraging AI and automation to transform data into actionable insights, driving efficiency and innovation. I also possess strong data visualization skills using Power BI and have a proven track record of improving process efficiency through test automation.',
            'skills': [
                'Python', 'Java', 'C', 'C++', 'JavaScript', 'PowerShell', 'Bash Scripting',
                'Django', 'Django REST Framework (DRF)', 'Selenium', 'Flask', 'Spring Boot',
                'MongoDB', 'SQL', 'PostgreSQL', 'Snowflake', 'AWS', 'GCP', 'Docker', 'Jenkins',
                'Linux', 'Git', 'Office 365', 'Postman', 'Jira', 'SAP S/4 HANA', 'Power BI',
                'DAX', 'Power Query', 'Figma'
            ],
            'experience': '''* **Engineering and Technical Services Excellence Co-op at Sanofi Pasteur (September 2023 - August 2024)**
* Developed cost-saving automation scripts using Selenium (Python) for SAP S/4 HANA, boosting process efficiency by 98% and saving over 150 hours annually.
* Led cross-functional collaboration with Metrology, Compliance, Maintenance, Project Management, Project Controls, and Supply Chain to deliver impactful technical solutions.
* Spearheaded the conceptualization, design, and management of Power BI dashboards, orchestrating development pipelines and implementing data transformation for improved decision-making.
* Mentored a co-op student in automation script writing and maintenance.

* **Project Support Assistant at University Technology Services, McMaster University (May 2023 - September 2023)**
* Automated the transition of McMaster's Electronic Distribution Lists (EDLs) to Microsoft Distribution Groups (DGs) using PowerShell scripts.
* Streamlined the extraction of EDL group members by developing an advanced automation script using Selenium (Python).
* Authored Microsoft 365 technical guides for faculty, students, and staff.

* **Backend Development Intern at Profundity (September 2021 - December 2021)**
* Designed and developed a student assessment platform with user authentication, test management, and result tracking using Django and Django REST Framework REST API.
* Engineered database architecture with Entity Relationship Diagrams and REST APIs.
* Led project milestones and daily scrums.

* **Web Development Intern at Bridging the Gaps Inc. (September 2020 - June 2021)**
* Conceptualized and developed a website to monitor users' health data.
* Employed Agile SDLC methodologies for requirement gathering, feature definition, and UX/UI design using Figma.
* Created relational database schema design and web application development using Django and Django Rest Framework.''',
            'projects': '''* **Air Doodling with Google Cloud Platform**
* Built using Google Vision AI and Evernote API.
* Implemented HSV value tracking, digital canvas projection, and text conversion of doodles.

* **Farm To Fork**
* Built using PHP.
* Implemented e-commerce functionality, text message product listing, OTP-verified delivery system, and backend automation.'''
        }

    def _generate_experience_html(self, experience_text):
        experience_html = ''
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
        return experience_html

    def _generate_projects_html(self, projects_text):
        projects_html = ''
        if projects_text:
            # Split the content into individual projects
            project_entries = []
            current_entry = []
            
            for line in projects_text.split('\n'):
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
        return projects_html

    def _generate_skills_html(self, skills):
        return ''.join([f'<span class="skill-badge">{skill}</span>' for skill in skills])

    def test_portfolio_generation(self):
        """Test portfolio generation using sample content"""
        # Create portfolio generator
        generator = PortfolioGenerator(self.user, self.template, self.resume)
        
        # Create a mock content generator that returns our sample content
        class MockContentGenerator:
            def __init__(self, *args, **kwargs):
                self.test_instance = self
            
            def generate_content(self):
                # Create HTML template with our sample content
                html_template = f'''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{self.test_instance.user.username} - Portfolio</title>
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
                </head>
                <body>
                    <!-- Hero Section -->
                    <section class="hero text-center">
                        <div class="container position-relative">
                            <h1 class="display-3 fw-bold">{self.test_instance.user.username}</h1>
                            <div class="about-content">
                                <p>{self.test_instance.sample_content['about']}</p>
                            </div>
                        </div>
                    </section>

                    <!-- Experience Section -->
                    <section class="section bg-light">
                        <div class="container">
                            <h2 class="text-center mb-5">Professional Experience</h2>
                            {self.test_instance._generate_experience_html(self.test_instance.sample_content['experience'])}
                        </div>
                    </section>

                    <!-- Projects Section -->
                    <section class="section">
                        <div class="container">
                            <h2 class="text-center mb-5">Projects</h2>
                            <div class="row">
                                {self.test_instance._generate_projects_html(self.test_instance.sample_content['projects'])}
                            </div>
                        </div>
                    </section>

                    <!-- Skills Section -->
                    <section class="section bg-light">
                        <div class="container">
                            <h2 class="text-center mb-5">Skills and Expertise</h2>
                            <div class="text-center">
                                {self.test_instance._generate_skills_html(self.test_instance.sample_content['skills'])}
                            </div>
                        </div>
                    </section>

                    <footer class="bg-dark text-white text-center py-4">
                        <div class="container">
                            <p>&copy; {datetime.now().year} {self.test_instance.user.username}. All rights reserved.</p>
                        </div>
                    </footer>

                    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
                </body>
                </html>
                '''
                return {
                    'html_content': html_template,
                    'raw_content': self.test_instance.sample_content
                }
        
        # Override the content generator with our mock
        generator.content_generator = MockContentGenerator()
        generator.content_generator.test_instance = self
        
        # Generate portfolio
        portfolio = generator.generate_portfolio()
        
        # Verify portfolio was created
        self.assertIsNotNone(portfolio)
        self.assertEqual(portfolio.user, self.user)
        self.assertEqual(portfolio.template, self.template)
        
        # Verify portfolio files were created
        portfolio_path = os.path.join('media', portfolio.portfolio_folder)
        self.assertTrue(os.path.exists(portfolio_path))
        self.assertTrue(os.path.exists(os.path.join(portfolio_path, 'index.html')))
        
        # Read the generated HTML
        with open(os.path.join(portfolio_path, 'index.html'), 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Verify content was properly rendered
        self.assertIn(self.sample_content['about'], html_content)
        for skill in self.sample_content['skills']:
            self.assertIn(skill, html_content)
        
        # Verify experiences were properly separated
        self.assertIn('Sanofi Pasteur', html_content)
        self.assertIn('McMaster University', html_content)
        self.assertIn('Profundity', html_content)
        self.assertIn('Bridging the Gaps Inc.', html_content)
        
        # Verify projects were properly rendered
        self.assertIn('Air Doodling with Google Cloud Platform', html_content)
        self.assertIn('Farm To Fork', html_content)
