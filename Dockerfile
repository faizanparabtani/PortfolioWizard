# =============================================================================
# Stage 1: Builder
# Installs Python + Node dependencies and compiles all assets.
# =============================================================================
FROM python:3.12-slim AS builder

# Install Node.js 20 and system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies into a virtual environment.
# Copy lockfile first so this layer is cached unless deps change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy the full source tree
COPY . .

# Build Tailwind CSS
RUN cd theme/static_src && npm ci && npm run build

# Collect static files.
# Real secrets are not needed at build time — Django only needs them at runtime.
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    GEMINI_API_KEY=build-time-placeholder \
    DJANGO_SETTINGS_MODULE=portfolio_site_generator.settings.production \
    uv run python manage.py collectstatic --noinput


# =============================================================================
# Stage 2: Runtime
# Minimal image — only what's needed to serve the application.
# =============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=portfolio_site_generator.settings.production

WORKDIR /app

# Copy the virtual environment and the application (including compiled assets)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

EXPOSE 8000

# Run migrations then start gunicorn.
# Railway injects DATABASE_URL automatically when a PostgreSQL plugin is attached.
CMD ["sh", "-c", \
    "python manage.py migrate --noinput && \
     gunicorn portfolio_site_generator.wsgi:application \
       --workers 2 \
       --timeout 120 \
       --bind 0.0.0.0:8000"]
