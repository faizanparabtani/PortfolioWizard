import json
import logging
from datetime import datetime
from pathlib import Path

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON schema for structured Claude output.
# ---------------------------------------------------------------------------
PORTFOLIO_SCHEMA = {
    "type": "object",
    "properties": {
        "about": {"type": "string"},
        "skills": {
            "type": "array",
            "items": {"type": "string"},
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "position":   {"type": "string"},
                    "company":    {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date":   {"type": "string"},
                    "bullets":    {"type": "array", "items": {"type": "string"}},
                },
                "required": ["position", "company", "start_date", "end_date", "bullets"],
                "additionalProperties": False,
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":        {"type": "string"},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                    "bullets":      {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "technologies", "bullets"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["about", "skills", "experience", "projects"],
    "additionalProperties": False,
}


class ContentGenerator:
    def __init__(self, resume_text, user, template):
        self.resume_text = resume_text
        self.user = user
        self.template = template
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY setting is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-opus-4-6"

    def generate_content(self):
        """Generate portfolio content using Claude API with structured JSON output."""
        try:
            logger.info("Starting content generation with Claude")
            return self._attempt_generation()
        except Exception:
            logger.exception("Content generation failed — falling back to defaults")
            return self._create_response(self._get_default_sections())

    # ---------------------------------------------------------------------- #
    # Private helpers                                                         #
    # ---------------------------------------------------------------------- #

    def _attempt_generation(self):
        prompt = self._build_prompt()
        logger.info("Calling Claude API for portfolio generation")
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "name": "portfolio_content",
                    "schema": PORTFOLIO_SCHEMA,
                }
            },
        ) as stream:
            response = stream.get_final_message()

        text = next(b.text for b in response.content if b.type == "text")
        sections = json.loads(text)
        logger.info("Structured JSON received from Claude")
        return self._create_response(sections)

    def _build_prompt(self):
        return (
            "You are a professional portfolio writer.\n\n"
            "Analyse the following resume and produce portfolio website content. "
            "Write the 'about' section in first person with 2-3 impactful sentences. "
            "Extract every skill, work experience entry, and project exactly as they "
            "appear in the resume — do not invent information.\n\n"
            f"RESUME:\n{self.resume_text}"
        )

    def _get_default_sections(self):
        return {
            "about": "Professional summary not available.",
            "skills": ["Content generation failed — please try again."],
            "experience": [],
            "projects": [],
        }

    def _create_response(self, sections):
        return {
            "html_content": self._build_html(sections),
            "raw_content": sections,
            "model_used": self.model,
        }

    def _build_html(self, sections: dict) -> str:
        """
        Populate a portfolio template with AI-generated content.

        Templates are plain HTML files that contain six simple markers:

            {{ about.title }}        — replaced with the user's full name
            {{ about.description }}  — replaced with the 2-3 sentence about text
            {{ current_year }}       — replaced with the current year (footer)
            <!-- SKILLS -->          — replaced with <span class="skill-badge"> elements
            <!-- EXPERIENCE -->      — replaced with experience-item blocks
            <!-- PROJECTS -->        — replaced with project-card blocks
        """
        template_path = (
            Path(settings.BASE_DIR) / self.template.template_folder / "index.html"
        )
        try:
            html = template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error("Template file not found at %s", template_path)
            raise

        # --- Scalar substitutions ------------------------------------------ #
        html = html.replace("{{ about.title }}", self.user.get_full_name() or self.user.username)
        html = html.replace("{{ about.description }}", sections.get("about", ""))
        html = html.replace("{{ current_year }}", str(datetime.now().year))

        # --- Skills --------------------------------------------------------- #
        skills_html = "".join(
            f'<span class="skill-badge">{skill}</span>'
            for skill in sections.get("skills", [])
        )
        html = html.replace("<!-- SKILLS -->", skills_html)

        # --- Experience ----------------------------------------------------- #
        experience_html = ""
        for exp in sections.get("experience", []):
            bullets = "".join(f"<li>{b}</li>" for b in exp.get("bullets", []))
            experience_html += (
                f'<div class="experience-item">'
                f'<div class="experience-header">'
                f'<span class="experience-company">{exp.get("company", "")}</span>'
                f'<span class="experience-position">{exp.get("position", "")}</span>'
                f'<span class="experience-duration">{exp.get("start_date", "")} – {exp.get("end_date", "")}</span>'
                f'</div>'
                f'<ul class="experience-bullets">{bullets}</ul>'
                f'</div>'
            )
        html = html.replace("<!-- EXPERIENCE -->", experience_html)

        # --- Projects ------------------------------------------------------- #
        projects_html = ""
        for project in sections.get("projects", []):
            techs = ", ".join(project.get("technologies", []))
            bullets = "".join(f"<p>{b}</p>" for b in project.get("bullets", []))
            projects_html += (
                f'<div class="project-card">'
                f'<h3 class="card-title">{project.get("title", "")}</h3>'
                f'<p class="card-technologies">{techs}</p>'
                f'<div class="card-text">{bullets}</div>'
                f'</div>'
            )
        html = html.replace("<!-- PROJECTS -->", projects_html)

        return html
