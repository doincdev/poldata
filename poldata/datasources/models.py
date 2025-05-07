from django.db import models
from django.utils import timezone
import os
from django.conf import settings

class DataSource(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    config = models.JSONField(
        blank=True, null=True,
        help_text="Configuration details including file path and metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_file_path(self):
        """Gets the full path to the CSV file."""
        if not self.config or 'file_path' not in self.config:
            return None
        return os.path.join(settings.MEDIA_ROOT, self.config['file_path'])

    def delete(self, *args, **kwargs):
        """Override delete to also remove the file."""
        file_path = self.get_file_path()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        super().delete(*args, **kwargs)

class CollectedData(models.Model):
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='collected_data')
    collected_at = models.DateTimeField(auto_now_add=True)
    validation_status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid')
    ], default='pending')
    processed = models.BooleanField(default=False)
    raw_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-collected_at']
        verbose_name_plural = 'Collected Data'

    def __str__(self):
        return f"{self.data_source.name} - {self.collected_at.strftime('%Y-%m-%d %H:%M')}"
