from django import forms
import os
import pandas as pd
from django.core.exceptions import ValidationError
from .models import DataSource

INPUT_CLASSES = "block w-full rounded-md border-0 py-1.5 px-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
TEXTAREA_CLASSES = "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
FILE_CLASSES = "block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"

class JSONWidget(forms.Textarea):
    def format_value(self, value):
        return value

class DataSourceForm(forms.ModelForm):
    uploaded_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': FILE_CLASSES,
            'accept': '.csv'
        })
    )

    class Meta:
        model = DataSource
        fields = ['name', 'description', 'config']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Enter a name for this CSV file'
            }),
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_CLASSES,
                'placeholder': 'Enter a description (optional)',
                'rows': 3
            }),
            'config': JSONWidget(attrs={
                'class': TEXTAREA_CLASSES,
                'rows': 4,
                'hidden': True
            })
        }
        error_messages = {
            'name': {
                'required': 'Please enter a name for the CSV file',
                'unique': 'A file with this name already exists'
            }
        }

    def clean_uploaded_file(self):
        file = self.cleaned_data.get('uploaded_file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB')
            
            # Check file extension
            ext = file.name.split('.')[-1].lower()
            if ext != 'csv':
                raise ValidationError('Only CSV files are allowed')
            
            # Validate CSV content
            try:
                df = pd.read_csv(file)
                if len(df.columns) == 0:
                    raise ValidationError('The CSV file appears to be empty')
                file.seek(0)  # Reset file pointer after reading
            except Exception as e:
                raise ValidationError(f'Invalid CSV file: {str(e)}')
            
            return file
        return None

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = cleaned_data.get('uploaded_file')
        
        if not uploaded_file and not self.instance.pk:
            raise ValidationError({
                'uploaded_file': 'Please upload a CSV file'
            })
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Initialize config if needed
        if instance.config is None:
            instance.config = {}
            
        if self.cleaned_data.get('uploaded_file'):
            uploaded_file = self.cleaned_data['uploaded_file']
            
            # Generate a unique filename
            filename = f"{instance.name}_{uploaded_file.name}"
            file_path = os.path.join('datasources', 'uploads', filename)
            
            # Ensure the uploads directory exists
            os.makedirs(os.path.join('media', 'datasources', 'uploads'), exist_ok=True)
            
            # Save the file
            full_path = os.path.join('media', file_path)
            with open(full_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Count total records
            try:
                df = pd.read_csv(full_path)
                total_records = len(df)
            except:
                total_records = 0
            
            # Store file info in config
            instance.config.update({
                'file_path': file_path,
                'original_filename': uploaded_file.name,
                'file_size': uploaded_file.size,
                'total_records': total_records,
                'content_type': uploaded_file.content_type
            })
        
        if commit:
            instance.save()
        return instance