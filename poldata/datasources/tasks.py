from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.db import transaction
import time
from .models import DataSource, CollectedData
from .connectors import get_connector_for_source
from .utils import (
    normalize_collected_data,
    validate_json_structure,
    calculate_credibility_score,
    generate_content_hash
)

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    rate_limit='60/h'
)
def collect_data_from_source(self, source_id):
    """Collect data from a specific source."""
    try:
        source = DataSource.objects.get(id=source_id)
        if not source.is_active:
            logger.info(f"Skipping inactive source: {source.name}")
            return

        logger.info(f"Starting data collection for {source.name}")
        connector = get_connector_for_source(source)
        
        # Collect data from source
        raw_data = connector.collect_data()
        
        # Normalize and validate data
        normalized_data = normalize_collected_data(raw_data, source.source_type)
        is_valid, validation_error = validate_json_structure(
            normalized_data,
            ['content', 'metadata', 'timestamp']
        )

        if not is_valid:
            logger.error(f"Data validation failed for {source.name}: {validation_error}")
            return

        # Generate content hash for deduplication
        content_hash = generate_content_hash(normalized_data['content'])
        
        # Check for duplicates
        if CollectedData.objects.filter(content_hash=content_hash).exists():
            logger.info(f"Duplicate content found for {source.name}, skipping")
            return

        # Create collected data record
        with transaction.atomic():
            collected_data = CollectedData.objects.create(
                data_source=source,
                raw_data=normalized_data,
                content_hash=content_hash,
                validation_status='valid'
            )
            
            # Schedule validation and processing
            validate_collected_data.delay(collected_data.id)
            process_collected_data.delay(collected_data.id)

        # Update source metadata
        source.last_collection = timezone.now()
        source.schedule_next_collection()
        source.save()

        logger.info(f"Successfully collected data from {source.name}")
        return collected_data.id

    except Exception as exc:
        logger.error(f"Error collecting data from {source_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True)
def validate_collected_data(self, collected_data_id):
    """Validate collected data and update its status."""
    try:
        data = CollectedData.objects.get(id=collected_data_id)
        data.validate_data()
        logger.info(f"Validated data {collected_data_id} with status: {data.validation_status}")
        
    except Exception as exc:
        logger.error(f"Error validating data {collected_data_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task(bind=True)
def process_collected_data(self, collected_data_id):
    """Process collected data and update source analytics."""
    try:
        data = CollectedData.objects.get(id=collected_data_id)
        source = data.data_source

        # Calculate credibility score
        score = calculate_credibility_score(data.raw_data, source.source_type)
        source.update_credibility_score(score)

        # Mark as processed
        data.processed = True
        data.save()

        logger.info(f"Processed data {collected_data_id} from {source.name}")

    except Exception as exc:
        logger.error(f"Error processing data {collected_data_id}: {str(exc)}")
        raise self.retry(exc=exc)

@shared_task
def schedule_data_collections():
    """Check and schedule data collections for active sources."""
    now = timezone.now()
    sources = DataSource.objects.filter(
        is_active=True,
        collection_frequency__in=['hourly', 'daily', 'weekly'],
        next_collection__lte=now
    )

    for source in sources:
        collect_data_from_source.delay(source.id)
        logger.info(f"Scheduled collection for {source.name}")

@shared_task
def update_source_analytics():
    """Update analytics for all active sources."""
    sources = DataSource.objects.filter(is_active=True)
    
    for source in sources:
        try:
            # Get recent collection statistics
            recent_collections = source.collected_data.filter(
                collected_at__gte=timezone.now() - timezone.timedelta(days=7)
            )
            
            analytics = {
                'total_collections': recent_collections.count(),
                'successful_collections': recent_collections.filter(
                    validation_status='valid'
                ).count(),
                'average_credibility': source.credibility_score,
                'last_updated': timezone.now().isoformat()
            }
            
            source.analytics = analytics
            source.save()
            
            logger.info(f"Updated analytics for {source.name}")
            
        except Exception as exc:
            logger.error(f"Error updating analytics for {source.name}: {str(exc)}")

@shared_task
def cleanup_old_data():
    """Clean up old collected data to prevent database bloat."""
    threshold = timezone.now() - timezone.timedelta(days=30)
    old_data = CollectedData.objects.filter(collected_at__lt=threshold)
    
    deleted_count = old_data.count()
    old_data.delete()
    
    logger.info(f"Cleaned up {deleted_count} old data records")
