from rest_framework import serializers
from .models import DataSource, CollectedData

class DataSourceSerializer(serializers.ModelSerializer):
    validation_status_display = serializers.CharField(source='get_validation_status_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'source_type_display', 'description',
            'config', 'credibility_score', 'validation_status',
            'validation_status_display', 'last_connection_test',
            'last_connection_error', 'is_active', 'collection_frequency',
            'next_collection', 'analytics', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'validation_status', 'last_connection_test', 'last_connection_error',
            'credibility_score', 'analytics', 'created_at', 'updated_at'
        ]

    def validate_config(self, value):
        """Validate the configuration based on source type."""
        source_type = self.initial_data.get('source_type')
        if not source_type:
            return value

        required_fields = {
            'twitter': ['api_key', 'api_secret', 'bearer_token'],
            'facebook': ['access_token'],
            'instagram': ['username', 'password'],
            'news': ['base_url'],
            'offline': ['file_path'],
        }

        if source_type in required_fields:
            missing = [field for field in required_fields[source_type] 
                      if field not in value]
            if missing:
                raise serializers.ValidationError(
                    f"Missing required config fields for {source_type}: {', '.join(missing)}"
                )
        return value

class CollectedDataSerializer(serializers.ModelSerializer):
    data_source = DataSourceSerializer(read_only=True)
    validation_status_display = serializers.CharField(source='get_validation_status_display', read_only=True)
    
    class Meta:
        model = CollectedData
        fields = [
            'id', 'data_source', 'collected_at', 'raw_data', 'validation_status',
            'validation_status_display', 'processed', 'processing_errors',
            'metadata', 'source_url', 'content_hash'
        ]
        read_only_fields = [
            'collected_at', 'validation_status', 'processed', 'processing_errors',
            'content_hash'
        ]

    def validate_raw_data(self, value):
        """Ensure the raw data is properly formatted."""
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Raw data must be a JSON object or array")
        return value
