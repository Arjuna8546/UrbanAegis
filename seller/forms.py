# forms.py
from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

class AdminLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'id': 'email',
            'required': True,
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'id': 'password',
            'required': True,
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    