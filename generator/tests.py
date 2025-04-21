from django.test import TestCase
from .services import ContentGenerator
from django.conf import settings
import logging
import google.generativeai as genai

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
            generator = ContentGenerator(test_resume)
            
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
