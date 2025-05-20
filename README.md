# PortfolioWizard 🧙

PortfolioWizard transforms your resume into a sleek personal website in minutes.

## 🔄 Flow

1. 📝 Upload PDF or DOCX resume  
2. 🤖 AI polishes content with Google Gemini 1.5 Pro  
3. ✍️ Live edit your text in the browser  
4. 🚀 One-click deploy to Netlify

[Take a look at one such site created and deployed with this project](https://faizanparabtani-site.netlify.app/)

## 🔍 Deeper Dive

### 🔧 Techniques
- Adaptive prompt engineering for Gemini 1.5 Pro  
- Exponential backoff with jitter for reliable API calls  
- Levenshtein distance for duplicate detection  
- HTML parsing & sanitization with BeautifulSoup4  
- Asynchronous tasks via Celery & Redis  

### Visuals
1. Dashboard to manage user uploaded Resumes and generate portfolio
![Dashboard](https://github.com/user-attachments/assets/b28316ed-1b98-46da-9b79-da930b02f054)

2. Selecting the style of portfolio with preview
![PortfolioSelect](https://github.com/user-attachments/assets/45296951-7d46-401d-8203-05d57277cc14)

3. Final Result
![Working Demo](https://github.com/user-attachments/assets/29eeb3ac-6c3c-4659-8cf2-4567358293a9)

![Working Demo1](https://github.com/user-attachments/assets/f152c063-5041-4c62-9ef8-80c057f3a005)

## 📂 Project Structure

```plaintext
portfolio_site_generator/
├── generator/
│   ├── services/
│   │   ├── [resume_parser.py](generator/services/resume_parser.py)
│   │   └── [content_generator.py](generator/services/content_generator.py)
│   └── templates/
├── media/           # Uploaded resumes & assets
├── portfolio_site_generator/  # Django settings & URLs
├── users/           # Authentication & profiles
└── manage.py
```

### 📦 Key Packages
- **Django** ≥4.2 — Web framework (https://www.djangoproject.com/)  
- **djangorestframework** — API layer (https://www.django-rest-framework.org/)  
- **google-generativeai** — Gemini API (https://pypi.org/project/google-generativeai/)  
- **netlify-python** — Netlify deployment (https://pypi.org/project/netlify-python/)  
- **python-dotenv** — Env var management (https://pypi.org/project/python-dotenv/)  
- **PyPDF2** & **pypdfium2** — PDF parsing (https://github.com/py-pdf/pypdfium2)  
- **pdfminer.six** & **pdfplumber** — Advanced PDF extraction (https://github.com/jsvine/pdfplumber)  
- **python-docx** — DOCX reading (https://python-docx.readthedocs.io/)  
- **beautifulsoup4** — HTML parsing (https://www.crummy.com/software/BeautifulSoup/)  
- **Levenshtein** — Text similarity (https://pypi.org/project/python-Levenshtein/)  
- **django-storages** & **boto3** — S3 media storage (https://django-storages.readthedocs.io/)  
- **whitenoise** — Static files serving (https://whitenoise.evans.io/)  
- **Tailwind CSS** — Styling (https://tailwindcss.com/)   
- **Roboto** font — Google Fonts (https://fonts.google.com/specimen/Roboto)  
