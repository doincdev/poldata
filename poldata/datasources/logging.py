import os
import logging.config

LOGGING = {
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
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/datasources.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'datasources': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'datasources.tasks': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'datasources.connectors': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Apply logging configuration
logging.config.dictConfig(LOGGING)

# Create logger instance for this module
logger = logging.getLogger('datasources')