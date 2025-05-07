from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def analytics_home(request):
    return render(request, 'analytics/home.html', {'title': 'Analytics Dashboard'})
