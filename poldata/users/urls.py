from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    home, register, profile, CustomLoginView,
    CustomPasswordResetView, CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView, CustomPasswordResetCompleteView
)

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(
        template_name='users/logout.html',
        next_page='login',
        http_method_names=['post', 'get']
    ), name='logout'),
    path('profile/', profile, name='profile'),
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]