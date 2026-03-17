import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Ensure logs directory exists
_LOG_DIR = BASE_DIR / 'logs'
_LOG_DIR.mkdir(exist_ok=True)

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(_LOG_DIR / 'app.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'generator': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'users': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}
