import os
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from generator.models import Resume
from generator.services import ResumeParser, ContentGenerator

class TestContentGeneration(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Sample resume text
        self.resume_text = """
        PROFESSIONAL SUMMARY
        Experienced software engineer with 5+ years in full-stack development.
        
        SKILLS
        - Python, Django, React
        - AWS, Docker, Kubernetes
        - CI/CD, Test Automation
        
        EXPERIENCE
        Senior Software Engineer | Tech Corp | 2020-Present
        - Led development of microservices architecture
        - Implemented automated testing pipeline
        
        Software Engineer | StartupCo | 2018-2020
        - Developed full-stack web applications
        - Mentored junior developers
        
        PROJECTS
        Portfolio Generator | 2023
        - Created automated portfolio generation system
        - Implemented AI-powered content generation
        """
        
        # Create test resume file
        self.resume_file = SimpleUploadedFile(
            "test_resume.txt",
            self.resume_text.encode('utf-8'),
            content_type="text/plain"
        )
        
        # Create resume object
        self.resume = Resume.objects.create(
            user=self.user,
            resume_file=self.resume_file
        )

    def test_resume_parsing(self):
        """Test if resume text is correctly extracted"""
        parser = ResumeParser(self.resume)
        parsed_text = parser.extract_text()
        
        # Check if main sections are present
        self.assertIn("PROFESSIONAL SUMMARY", parsed_text)
        self.assertIn("SKILLS", parsed_text)
        self.assertIn("EXPERIENCE", parsed_text)
        self.assertIn("PROJECTS", parsed_text)
        
        # Check specific content
        self.assertIn("Experienced software engineer", parsed_text)
        self.assertIn("Python, Django, React", parsed_text)

    def test_content_generation(self):
        """Test if content is generated correctly"""
        # First parse the resume
        parser = ResumeParser(self.resume)
        parsed_text = parser.extract_text()
        
        # Generate content
        generator = ContentGenerator(parsed_text)
        content = generator.generate_content()
        
        # Check if all required sections are present
        self.assertIn('about', content)
        self.assertIn('experience', content)
        self.assertIn('skills', content)
        self.assertIn('projects', content)
        
        # Check if sections have meaningful content
        self.assertTrue(len(content['about']) > 50)  # About section should be substantial
        self.assertTrue(isinstance(content['skills'], list))  # Skills should be a list
        self.assertTrue(len(content['experience']) >= 2)  # Should have at least 2 experiences
        self.assertTrue(len(content['projects']) >= 1)  # Should have at least 1 project

    def tearDown(self):
        # Clean up created files
        if self.resume.resume_file:
            if os.path.exists(self.resume.resume_file.path):
                os.remove(self.resume.resume_file.path) 