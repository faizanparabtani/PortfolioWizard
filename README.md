# PortfolioWizard

PortfolioWizard is a comprehensive tool designed to transform professional resumes into sleek, deployable personal websites. By leveraging advanced natural language processing and modern web technologies, it streamlines the process of creating a digital portfolio.

## Workflow

The application follows a structured four-step process to generate a portfolio:

1.  **Resume Upload**: Users upload their existing resume in PDF or DOCX format.
2.  **Content Enhancement**: The system utilizes Google's Gemini 1.5 Pro AI model to parse, analyze, and polish the resume content for a web presentation.
3.  **Live Editing**: Users are presented with a live editor to refine the generated text and verify the content.
4.  **Deployment**: With a single interaction, the finalized site is deployed to Netlify.

[View a sample portfolio created with PortfolioWizard](https://faizanparabtani-site.netlify.app/)

## Technical Architecture

This project incorporates several advanced engineering techniques to ensure reliability and performance:

*   **Adaptive Prompt Engineering**: Optimizes interactions with the Gemini 1.5 Pro API for consistent results.
*   **Resilient API Communication**: Implements exponential backoff with jitter to handle API rate limits and network instability.
*   **Duplicate Detection**: Uses Levenshtein distance algorithms to identify and merge redundant content.
*   **Robust Parsing**: Employs `BeautifulSoup4` for HTML sanitization and structure management.
*   **Asynchronous Processing**: (Planned/Implemented) Task queue integration via Celery and Redis for handling long-running generation tasks.

## User Interface

### Dashboard
The central hub for managing uploaded resumes and initiating the generation process.
![Dashboard](https://github.com/user-attachments/assets/b28316ed-1b98-46da-9b79-da930b02f054)

### Template Selection
Users can select their preferred aesthetic from a collection of templates with real-time previews.
![PortfolioSelect](https://github.com/user-attachments/assets/45296951-7d46-401d-8203-05d57277cc14)

### Generated Portfolio
The final deployed output, responsive and professional.
![Working Demo](https://github.com/user-attachments/assets/29eeb3ac-6c3c-4659-8cf2-4567358293a9)
![Working Demo1](https://github.com/user-attachments/assets/f152c063-5041-4c62-9ef8-80c057f3a005)

## Project Structure

```plaintext
portfolio_site_generator/
├── generator/
│   ├── services/
│   │   ├── resume_parser.py        # Logic for extracting text from PDF/DOCX
│   │   └── content_generator.py    # AI integration for content refinement
│   └── templates/                  # Django templates for the generator UI
├── media/                          # Directory for uploaded user assets
├── portfolio_site_generator/       # Core Django settings and configuration
├── users/                          # User authentication and profile management
└── manage.py                       # Django command-line utility
```

## Key Dependencies

*   **Django** (≥4.2): The high-level Python web framework.
*   **Django REST Framework**: For building Web APIs.
*   **google-generativeai**: Client library for the Gemini API.
*   **netlify-python**: Interface for Netlify deployments.
*   **python-dotenv**: Loads environment variables from `.env` files.
*   **PyPDF2** & **pypdfium2**: Libraries for reading PDF files.
*   **pdfminer.six** & **pdfplumber**: Advanced tools for PDF data extraction.
*   **python-docx**: Library for reading Microsoft Word documents.
*   **beautifulsoup4**: Library for parsing HTML and XML documents.
*   **Levenshtein**: For computing string similarities.
*   **django-storages** & **boto3**: For managing file storage on AWS S3 (optional configuration).
*   **whitenoise**: Simplified static file serving for web apps.
*   **Tailwind CSS**: Utility-first CSS framework for styling.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.