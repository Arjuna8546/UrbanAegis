# your_app_name/pipeline.py

from django.contrib.auth import login
from django.shortcuts import redirect
from core.models import Users
from django.contrib import messages
from django.db.models import Q

def create_user(strategy, details, backend, request, user=None, *args, **kwargs):
    fields = {
        'email': details.get('email'),
        'first_name': details.get('first_name'),
        'last_name': details.get('last_name'),
    }

    if not fields['email']:
        return  # Email is required, so we skip if not provided

    # Check if the user already exists and active
    existing_user = Users.objects.filter(Q(email=fields['email'])).first()
    
    if existing_user:
        # Check if the existing user is inactive
        if not existing_user.is_active:
            # Redirect or handle inactive account
            return redirect('inactive_account_page')  # Redirect to a specific page for inactive users

        # If active, proceed with login
        login(request, existing_user, backend='social_core.backends.google.GoogleOAuth2')
        return redirect('home')

    # If the user does not exist, create a new one
    user = Users(
        email=fields['email'],
        first_name=fields['first_name'],
        last_name=fields['last_name'],
        is_google="True"
        
    )
    user.set_unusable_password()  # No password for social login users
    user.save()

    login(request, user, backend='social_core.backends.google.GoogleOAuth2')
    return redirect('home')
