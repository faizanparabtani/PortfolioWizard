import os
import json
import PyPDF2
import requests
import logging
from django.conf import settings
from .models import Resume, GeneratedPortfolio

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
        self.api_key = settings.HUGGINGFACE_API_KEY
        if not self.api_key:
            raise ValueError("Hugging Face API key is required")
        
        self.api_url = "https://api-inference.huggingface.co/models/"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Default models for different tasks
        self.models = {
            'text_generation': "gpt2",
            'summarization': "facebook/bart-large-cnn",
            'classification': "distilbert-base-uncased"
        }

    def _make_api_call(self, model: str, payload: dict) -> dict:
        """Make an API call to Hugging Face."""
        try:
            api_url = f"{self.api_url}{model}"
            logger.info(f"Making API call to {model}")
            response = requests.post(api_url, headers=self.headers, json=payload)
            response.raise_for_status()  # Raise exception for bad status codes
            result = response.json()
            logger.info(f"API call successful: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {str(e)}")
            raise

    def generate_content(self):
        """Generate portfolio content using Hugging Face AI"""
        try:
            logger.info("Starting content generation")
            logger.debug(f"Resume text length: {len(self.resume_text)}")
            
            sections = self._split_resume_into_sections()
            logger.info("Resume split into sections")
            
            content = {
                "about": {
                    "title": "Professional Summary",
                    "content": self._generate_about(sections.get('about', ''))
                },
                "experience": {
                    "title": "Work Experience",
                    "content": self._generate_experience(sections.get('experience', ''))
                },
                "skills": {
                    "title": "Skills & Expertise",
                    "content": self._generate_skills(sections.get('skills', ''))
                },
                "projects": {
                    "title": "Projects",
                    "content": self._generate_projects(sections.get('projects', ''))
                }
            }
            
            logger.info("Content generation completed successfully")
            return content
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise

    def _split_resume_into_sections(self) -> dict:
        """Split resume text into relevant sections."""
        # Simple split based on length - you might want to implement
        # more sophisticated parsing based on your resume format
        text_length = len(self.resume_text)
        section_size = text_length // 4
        
        return {
            'about': self.resume_text[:section_size],
            'experience': self.resume_text[section_size:section_size*2],
            'skills': self.resume_text[section_size*2:section_size*3],
            'projects': self.resume_text[section_size*3:]
        }

    def _generate_about(self, text):
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": 150,
                "min_length": 50,
                "do_sample": True
            }
        }
        result = self._make_api_call(self.models['summarization'], payload)
        return result[0]['summary_text'] if isinstance(result, list) else result['summary_text']

    def _generate_experience(self, text):
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": 200,
                "min_length": 50,
                "do_sample": True
            }
        }
        result = self._make_api_call(self.models['text_generation'], payload)
        return result[0]['generated_text'] if isinstance(result, list) else result['generated_text']

    def _generate_skills(self, text):
        # First, extract skills
        skills = [skill.strip() for skill in text.split(',') if skill.strip()]
        
        # Then categorize them
        payload = {
            "inputs": text,
            "parameters": {
                "candidates": ["Frontend", "Backend", "DevOps", "Database", "Other"]
            }
        }
        categories = self._make_api_call(self.models['classification'], payload)
        
        # Format skills with categories
        categorized_skills = []
        for skill in skills:
            categorized_skills.append({
                'name': skill,
                'category': categories[0]['label'],
                'level': min(int(float(categories[0]['score']) * 100), 100)
            })
        
        return json.dumps(categorized_skills)

    def _generate_projects(self, text):
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": 150,
                "min_length": 50,
                "do_sample": True
            }
        }
        result = self._make_api_call(self.models['text_generation'], payload)
        return result[0]['generated_text'] if isinstance(result, list) else result['generated_text']

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