from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordResetView, 
    PasswordResetDoneView, PasswordResetConfirmView,
    PasswordResetCompleteView
)
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm, UserPasswordChangeForm, LoginForm
from django.contrib.auth import update_session_auth_hash
import logging

logger = logging.getLogger(__name__)

def home(request):
    try:
        return render(request, 'home.html', {'title': 'Home'})
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}")
        messages.error(request, "An error occurred. Please try again later.")
        return render(request, 'home.html', {'title': 'Home'}, status=500)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Akun berhasil dibuat untuk {username}! Anda sekarang dapat login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginForm

class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'
    
class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    
class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        password_form = UserPasswordChangeForm(request.user, request.POST)
        
        if 'update_profile' in request.POST:
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Akun Anda berhasil diperbarui!')
                return redirect('profile')
        elif 'change_password' in request.POST:
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password Anda berhasil diperbarui!')
                return redirect('profile')
            else:
                messages.error(request, 'Harap perbaiki kesalahan di bawah ini.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        password_form = UserPasswordChangeForm(request.user)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'password_form': password_form
    }

    return render(request, 'users/profile.html', context)