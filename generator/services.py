import os
import json
import PyPDF2
from django.conf import settings
from .models import Resume, GeneratedPortfolio

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

    def generate_content(self):
        """Generate portfolio content using AI"""
        # This is a placeholder for AI content generation
        # You would integrate with an AI service here (e.g., OpenAI, Anthropic, etc.)
        content = {
            "about": {
                "title": "Professional Summary",
                "content": self._generate_about()
            },
            "experience": {
                "title": "Work Experience",
                "content": self._generate_experience()
            },
            "skills": {
                "title": "Skills & Expertise",
                "content": self._generate_skills()
            },
            "projects": {
                "title": "Projects",
                "content": self._generate_projects()
            }
        }
        return content

    def _generate_about(self):
        # Placeholder for AI-generated about section
        return "A brief professional summary based on your resume."

    def _generate_experience(self):
        # Placeholder for AI-generated experience section
        return "Detailed work experience based on your resume."

    def _generate_skills(self):
        # Placeholder for AI-generated skills section
        return "List of skills and expertise based on your resume."

    def _generate_projects(self):
        # Placeholder for AI-generated projects section
        return "Highlighted projects based on your resume."

class PortfolioGenerator:
    def __init__(self, user, template, resume):
        self.user = user
        self.template = template
        self.resume = resume

    def generate_portfolio(self):
        """Generate a personalized portfolio"""
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

    def _generate_portfolio_files(self, portfolio, content):
        """Generate the actual portfolio files"""
        template_path = os.path.join(settings.BASE_DIR, self.template.template_folder)
        portfolio_path = os.path.join(settings.MEDIA_ROOT, portfolio.portfolio_folder)

        # Create portfolio directory
        os.makedirs(portfolio_path, exist_ok=True)

        # Copy and modify template files
        for root, dirs, files in os.walk(template_path):
            for file in files:
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, template_path)
                dst_path = os.path.join(portfolio_path, rel_path)

                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                # Process and copy file
                if file.endswith(('.html', '.css', '.js')):
                    self._process_template_file(src_path, dst_path, content)
                else:
                    # Copy other files as is
                    with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                        dst.write(src.read())

    def _process_template_file(self, src_path, dst_path, content):
        """Process template files and replace placeholders with generated content"""
        with open(src_path, 'r', encoding='utf-8') as src:
            template_content = src.read()

        # Replace placeholders with actual content
        # This is a simple example - you might want to use a proper template engine
        processed_content = template_content
        for section, data in content.items():
            processed_content = processed_content.replace(
                f"{{{{ {section}.title }}}}", data['title']
            )
            processed_content = processed_content.replace(
                f"{{{{ {section}.content }}}}", data['content']
            )

        with open(dst_path, 'w', encoding='utf-8') as dst:
            dst.write(processed_content) 