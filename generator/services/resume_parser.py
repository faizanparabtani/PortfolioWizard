import PyPDF2
import logging

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
            logger.error(f"Error extracting text from PDF: {str(e)}")
        return text 