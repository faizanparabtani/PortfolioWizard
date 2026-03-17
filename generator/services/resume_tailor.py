import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

TAILOR_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
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
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["position", "company", "start_date", "end_date", "bullets"],
                "additionalProperties": False,
            },
        },
        "keywords_matched": {
            "type": "array",
            "items": {"type": "string"},
        },
        "keywords_missing": {
            "type": "array",
            "items": {"type": "string"},
        },
        "ats_score": {"type": "integer"},
        "changes_summary": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "summary", "skills", "experience",
        "keywords_matched", "keywords_missing", "ats_score", "changes_summary",
    ],
    "additionalProperties": False,
}


class ResumeTailor:
    def __init__(self, resume_text: str, job_description: str):
        self.resume_text = resume_text
        self.job_description = job_description
        api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY setting is required")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-opus-4-6"

    def tailor(self) -> dict:
        """Return structured tailored resume content."""
        prompt = (
            "You are an expert resume writer and ATS specialist.\n\n"
            "Given the RESUME and JOB DESCRIPTION below, tailor the resume to maximise "
            "relevance. Rewrite the summary and experience bullets using language and "
            "keywords from the job description. Reorder skills so the most relevant appear "
            "first. Do not invent experience or credentials that are not in the original "
            "resume — only reframe and emphasise what is already there.\n\n"
            f"RESUME:\n{self.resume_text}\n\n"
            f"JOB DESCRIPTION:\n{self.job_description}"
        )
        logger.info("Calling Claude API for resume tailoring")
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "name": "tailored_resume",
                    "schema": TAILOR_SCHEMA,
                }
            },
        ) as stream:
            response = stream.get_final_message()

        text = next(b.text for b in response.content if b.type == "text")
        if not text:
            raise ValueError("Empty response from Claude")
        return json.loads(text)
