from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, PasswordChangeForm, AuthenticationForm
from .models import Profile

INPUT_CLASSES = "block w-full rounded-md border-0 py-1.5 px-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Enter your username"
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Enter your password"
    }))

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Enter your email"
    }))
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Choose a username"
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Create a password"
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Confirm password"
    }))

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email sudah digunakan.")
        return email

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": INPUT_CLASSES
    }))
    username = forms.CharField(widget=forms.TextInput(attrs={
        "class": INPUT_CLASSES
    }))

    class Meta:
        model = User
        fields = ["username", "email"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["image"]
        widgets = {
            "image": forms.FileInput(attrs={
                "class": "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
            })
        }

class UserPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Current Password"
    }))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "New Password"
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": INPUT_CLASSES,
        "placeholder": "Confirm New Password"
    }))

    class Meta:
        model = User
        fields = ["old_password", "new_password1", "new_password2"]