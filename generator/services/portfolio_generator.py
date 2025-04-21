import os
import logging
from django.conf import settings
from .resume_parser import ResumeParser
from .content_generator import ContentGenerator
from ..models import GeneratedPortfolio

logger = logging.getLogger(__name__)

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
            content_generator = ContentGenerator(resume_text, self.user, self.template)
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