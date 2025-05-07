from django.contrib import admin
from django.utils.html import format_html
from .models import DataSource, CollectedData

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'file_info', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def file_info(self, obj):
        if obj.config and 'original_filename' in obj.config:
            file_size = obj.config.get('file_size', 0)
            size_str = f"{file_size / (1024*1024):.1f} MB" if file_size else "Unknown size"
            return format_html(
                "<strong>File:</strong> {} <br><strong>Size:</strong> {} <br><strong>Records:</strong> {}",
                obj.config['original_filename'],
                size_str,
                obj.config.get('total_records', 'Unknown')
            )
        return "No file uploaded"
    file_info.short_description = "File Information"

@admin.register(CollectedData)
class CollectedDataAdmin(admin.ModelAdmin):
    list_display = ('data_source', 'collected_at', 'validation_status', 'processed')
    list_filter = ('validation_status', 'processed')
    search_fields = ('data_source__name',)
    readonly_fields = ('raw_data', 'collected_at',)
