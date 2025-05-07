// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger reflow
    toast.offsetHeight;

    // Show toast
    toast.classList.add('show');

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Data Source Management
async function testConnection(sourceId) {
    try {
        const response = await fetch(`/api/datasources/sources/${sourceId}/test_connection/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Connection test failed');
        }
        
        showToast(`Connection test ${data.validation_status}`, data.validation_status === 'valid' ? 'success' : 'error');
        
        if (data.validation_status === 'valid') {
            setTimeout(() => location.reload(), 1000);
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error testing connection', 'error');
    }
}

async function collectData(sourceId) {
    try {
        const response = await fetch(`/api/datasources/sources/${sourceId}/collect_data/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to start data collection');
        }
        
        showToast('Data collection started successfully');
        
        // Add loading indicator to the row
        const row = document.querySelector(`tr[data-source-id="${sourceId}"]`);
        if (row) {
            row.classList.add('animate-pulse');
            setTimeout(() => row.classList.remove('animate-pulse'), 2000);
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error starting data collection', 'error');
    }
}

function downloadFile(sourceId) {
    window.location.href = `/api/datasources/sources/${sourceId}/download_file/`;
}

// Modal Management
function openModal() {
    const modal = document.getElementById('sourceFormModal');
    if (modal) {
        modal.classList.remove('hidden');
        // Focus first input
        const firstInput = modal.querySelector('input:not([type="hidden"])');
        if (firstInput) {
            firstInput.focus();
        }
    }
}

function closeModal() {
    const modal = document.getElementById('sourceFormModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Form Handling
document.addEventListener('DOMContentLoaded', function() {
    const sourceForm = document.getElementById('sourceForm');
    const sourceTypeSelect = document.getElementById('source_type');
    
    if (sourceTypeSelect) {
        sourceTypeSelect.addEventListener('change', function() {
            const configDiv = document.getElementById('dynamicConfig');
            const fileUploadSection = document.getElementById('fileUploadSection');
            
            if (!configDiv) return;
            
            configDiv.innerHTML = '';
            
            const sourceType = this.value;
            if (fileUploadSection) {
                fileUploadSection.classList.toggle('hidden', sourceType !== 'offline');
            }
            
            if (sourceType && configTemplates[sourceType]) {
                configTemplates[sourceType].forEach(field => {
                    configDiv.appendChild(createConfigField(field));
                });
            }
        });
    }

    if (sourceForm) {
        sourceForm.addEventListener('submit', handleSourceFormSubmit);
    }
});

async function handleSourceFormSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const configData = {};
    
    for (let [key, value] of formData.entries()) {
        if (key.startsWith('config_')) {
            configData[key.replace('config_', '')] = value;
        }
    }
    
    const sourceData = new FormData();
    sourceData.append('name', formData.get('name'));
    sourceData.append('source_type', formData.get('source_type'));
    sourceData.append('description', formData.get('description'));
    sourceData.append('collection_frequency', formData.get('collection_frequency'));
    sourceData.append('is_active', formData.get('is_active') === 'on');
    sourceData.append('config', JSON.stringify(configData));
    
    const fileInput = formData.get('uploaded_file');
    if (fileInput && fileInput.size > 0) {
        sourceData.append('uploaded_file', fileInput);
    }
    
    try {
        const response = await fetch('/api/datasources/sources/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: sourceData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to save data source');
        }
        
        showToast('Data source created successfully');
        setTimeout(() => location.reload(), 1000);
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Error saving data source', 'error');
    }
}