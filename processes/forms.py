# Django Authentication System with Secure Credentials

# Step 1: Project Setup
# Assuming you have Django installed, let's organize the project

# models.py - Custom User Model (recommended over the default User model)



# forms.py - Registration and Login Forms
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    """Custom registration form based on Django's UserCreationForm"""
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def clean_email(self):
        """Validate that the email is not already in use"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email address is already in use.")
        return email
    
    def save(self, commit=True):
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    """Custom login form based on Django's AuthenticationForm"""
    username = forms.EmailField(label='Email Address', widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Password'}))


# views.py - Signup and Login Views



# urls.py - URL Configuration for Authentication



