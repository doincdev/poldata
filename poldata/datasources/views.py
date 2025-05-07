import os
import pandas as pd
from collections import Counter
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.conf import settings
from .models import DataSource, CollectedData
from .forms import DataSourceForm

def read_csv_file(file_path, max_rows=10):
    """Read CSV file and return a preview of its contents."""
    try:
        df = pd.read_csv(file_path)
        total_records = len(df)
        preview_data = df.head(max_rows)
        
        return {
            'success': True,
            'total_records': total_records,
            'total_columns': len(df.columns),
            'columns': df.columns.tolist(),
            'data': preview_data.values.tolist()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@method_decorator(login_required, name='dispatch')
class DashboardView(ListView):
    model = DataSource
    template_name = 'datasources/dashboard.html'
    context_object_name = 'sources'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sources'] = self.model.objects.count()
        return context

@method_decorator(login_required, name='dispatch')
class DataSourceCreateView(CreateView):
    model = DataSource
    template_name = 'datasources/datasource_form.html'
    form_class = DataSourceForm
    success_url = reverse_lazy('datasource-dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'CSV file uploaded successfully.')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class DataSourceDetailView(DetailView):
    model = DataSource
    template_name = 'datasources/datasource_detail.html'
    context_object_name = 'source'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add file preview
        if self.object.config.get('file_path'):
            file_path = os.path.join(settings.MEDIA_ROOT, self.object.config['file_path'])
            if os.path.exists(file_path):
                preview_result = read_csv_file(file_path)
                if preview_result['success']:
                    context['preview_data'] = preview_result
                else:
                    context['preview_error'] = preview_result['error']
        
        return context

    def preview_file(self, request, *args, **kwargs):
        self.object = self.get_object()
        file_path = self.object.get_file_path()
        
        if not file_path or not os.path.exists(file_path):
            messages.error(request, "File not found")
            return redirect('datasource-detail', pk=self.object.pk)
        
        filename = os.path.basename(file_path)
        search_query = request.GET.get('search', '').lower()
        column_filter = request.GET.get('column')
        
        try:
            df = pd.read_csv(file_path)
            total_records = len(df)
            
            # Apply filters if present
            if search_query:
                if column_filter and column_filter in df.columns:
                    mask = df[column_filter].astype(str).str.lower().str.contains(search_query)
                    df = df[mask]
                else:
                    mask = df.astype(str).apply(lambda x: x.str.lower().str.contains(search_query)).any(axis=1)
                    df = df[mask]

            total_filtered = len(df)
            preview_data = df.head(10)
            
            # Calculate word statistics for text columns
            word_stats = {}
            for column in df.columns:
                if df[column].dtype == 'object':
                    text_data = ' '.join(df[column].astype(str).values)
                    words = text_data.lower().split()
                    word_count = len(words)
                    unique_words = len(set(words))
                    most_common = Counter(words).most_common(5)
                    
                    word_stats[column] = {
                        'total_words': word_count,
                        'unique_words': unique_words,
                        'most_common': most_common,
                        'word_density': round(unique_words / word_count * 100, 2) if word_count > 0 else 0
                    }
            
            context = self.get_context_data(
                filename=filename,
                total_records=total_records,
                total_filtered=total_filtered,
                columns=df.columns.tolist(),
                data=preview_data.values.tolist(),
                search_query=search_query,
                column_filter=column_filter,
                word_stats=word_stats
            )
            
            self.template_name = 'datasources/preview_file.html'
            return self.render_to_response(context)
            
        except pd.errors.EmptyDataError:
            messages.error(request, "The CSV file is empty or has no valid data")
            return redirect('datasource-detail', pk=self.object.pk)
        except Exception as e:
            messages.error(request, f"Error previewing file: {str(e)}")
            return redirect('datasource-detail', pk=self.object.pk)

@method_decorator(login_required, name='dispatch')
class DataSourceUpdateView(UpdateView):
    model = DataSource
    form_class = DataSourceForm
    template_name = 'datasources/datasource_form.html'
    
    def get_success_url(self):
        return reverse_lazy('datasource-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'CSV file details updated successfully.')
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class DataSourceDeleteView(DeleteView):
    model = DataSource
    template_name = 'datasources/datasource_confirm_delete.html'
    success_url = reverse_lazy('datasource-dashboard')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'CSV file deleted successfully.')
        return super().delete(request, *args, **kwargs)

@login_required
def export_source_data(request, pk):
    """Export source data as CSV or JSON."""
    format = request.GET.get('format', 'csv')
    
    if pk == 'all':
        # Export data from all sources
        sources = DataSource.objects.all()
        data = []
        for source in sources:
            file_path = source.get_file_path()
            if file_path and os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    data.append({
                        'source_name': source.name,
                        'data': df.to_dict('records')
                    })
                except Exception as e:
                    messages.warning(request, f"Error reading {source.name}: {str(e)}")
        
        if format == 'json':
            response = HttpResponse(content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename="all_sources.json"'
            import json
            json.dump(data, response)
        else:
            # Combine all CSVs
            all_data = []
            for source_data in data:
                df = pd.DataFrame(source_data['data'])
                df['source_name'] = source_data['source_name']
                all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="all_sources.csv"'
                combined_df.to_csv(response, index=False)
            else:
                messages.error(request, "No valid data found to export")
                return redirect('datasource-dashboard')
    else:
        # Export single source
        source = DataSource.objects.get(pk=pk)
        file_path = source.get_file_path()
        
        if not file_path or not os.path.exists(file_path):
            messages.error(request, "File not found")
            return redirect('datasource-detail', pk=pk)
        
        try:
            df = pd.read_csv(file_path)
            if format == 'json':
                response = HttpResponse(content_type='application/json')
                response['Content-Disposition'] = f'attachment; filename="{source.config.get("original_filename", "data")}.json"'
                df.to_json(response, orient='records')
            else:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{source.config.get("original_filename", "data.csv")}"'
                df.to_csv(response, index=False)
        except Exception as e:
            messages.error(request, f"Error exporting file: {str(e)}")
            return redirect('datasource-detail', pk=pk)
    
    return response

@method_decorator(login_required, name='dispatch')
class CollectionHistoryView(ListView):
    model = CollectedData
    template_name = 'datasources/collection_history.html'
    context_object_name = 'collections'
    paginate_by = 20

    def get_queryset(self):
        return CollectedData.objects.select_related('data_source').order_by('-collected_at')

@method_decorator(login_required, name='dispatch')
class DataSourceSettingsView(TemplateView):
    template_name = 'datasources/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sources'] = DataSource.objects.count()
        return context
