import re

# Pre-compiled patterns for performance
_SCRIPT_RE = re.compile(
    r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
    flags=re.IGNORECASE | re.DOTALL,
)
_EVENT_ATTR_DOUBLE_RE = re.compile(r'\s+on\w+="[^"]*"', flags=re.IGNORECASE)
_EVENT_ATTR_SINGLE_RE = re.compile(r"\s+on\w+='[^']*'", flags=re.IGNORECASE)
_JS_URL_RE = re.compile(r'''(href|src)=["']javascript:[^"']*["']''', flags=re.IGNORECASE)


def sanitize_html(html: str) -> str:
    """Strip script tags, event-handler attributes, and javascript: URLs from HTML.

    Used to clean user-edited portfolio HTML before persisting it to the database.
    This is a defence-in-depth measure; the CSP header on serve_portfolio is the
    primary XSS mitigation.
    """
    html = _SCRIPT_RE.sub('', html)
    html = _EVENT_ATTR_DOUBLE_RE.sub('', html)
    html = _EVENT_ATTR_SINGLE_RE.sub('', html)
    html = _JS_URL_RE.sub('', html)
    return html
