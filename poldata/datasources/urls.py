from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='datasource-dashboard'),
    path('create/', views.DataSourceCreateView.as_view(), name='datasource-create'),
    path('<int:pk>/', views.DataSourceDetailView.as_view(), name='datasource-detail'),
    path('<int:pk>/edit/', views.DataSourceUpdateView.as_view(), name='datasource-edit'),
    path('<int:pk>/delete/', views.DataSourceDeleteView.as_view(), name='datasource-delete'),
    path('<int:pk>/preview/', views.DataSourceDetailView.as_view(template_name='datasources/preview_file.html'), {'action': 'preview_file'}, name='preview-file'),
    re_path(r'^(?P<pk>\d+|all)/export/$', views.export_source_data, name='datasource-export'),
    path('collection-history/', views.CollectionHistoryView.as_view(), name='collection-history'),
    path('settings/', views.DataSourceSettingsView.as_view(), name='datasource-settings'),
]
