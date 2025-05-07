from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'datasources.settings')

app = Celery('datasources')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from all registered Django app configs
app.autodiscover_tasks()

# Configure task queues
app.conf.task_queues = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'data_collection': {
        'exchange': 'data_collection',
        'routing_key': 'data_collection',
    },
    'data_processing': {
        'exchange': 'data_processing',
        'routing_key': 'data_processing',
    },
}

# Task routing
app.conf.task_routes = {
    'datasources.tasks.collect_data_from_source': {'queue': 'data_collection'},
    'datasources.tasks.validate_collected_data': {'queue': 'data_processing'},
    'datasources.tasks.process_collected_data': {'queue': 'data_processing'},
    'datasources.tasks.update_source_analytics': {'queue': 'data_processing'},
}

# Celery Beat Schedule
app.conf.beat_schedule = {
    'schedule-collections': {
        'task': 'datasources.tasks.schedule_data_collections',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
    'update-analytics': {
        'task': 'datasources.tasks.update_source_analytics',
        'schedule': crontab(hour='*/1'),  # Run every hour
    },
}

# Configure rate limiting
app.conf.task_annotations = {
    'datasources.tasks.collect_data_from_source': {
        'rate_limit': '60/h'  # Limit to 60 collections per hour
    },
}

# Additional Celery configurations
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_always_eager=False,  # Set to True for development/testing
    task_eager_propagates=True,
    worker_prefetch_multiplier=1,  # Prevent worker from prefetching too many tasks
    task_acks_late=True,  # Only acknowledge task after it's completed
    task_reject_on_worker_lost=True,  # Reject tasks if worker disconnects
    task_default_rate_limit='100/h',  # Default rate limit for all tasks
)
