from django.shortcuts import render,redirect
from django.views.generic import TemplateView
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from user.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

class AccountDetail(TemplateView):
    template_name = 'account_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add the user to the context if they are authenticated
        if self.request.user.is_authenticated:
            context['user'] = self.request.user
        return context
    
    def post(self, request):
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_no = request.POST.get('phone_no')
        
        user = self.request.user
        errors = {}

        # Validate first and last name (ensure they’re not empty)
        if not first_name:
            errors['first_name'] = "First name cannot be empty."
        if not last_name:
            errors['last_name'] = "Last name cannot be empty."

        # Validate email format
        if email:
            try:
                validate_email(email)
                user.email = email  # Only set email if validation succeeds
            except ValidationError:
                errors['email'] = "Invalid email format."
        else:
            errors['email'] = "Email cannot be empty."

        # Validate phone number (optional check for numeric values)
        if phone_no and not phone_no.isdigit():
            errors['phone_no'] = "Phone number must contain only digits."
        else:
            user.phone_no = phone_no  # Ensure the `phone_no` field exists in the user model

        # If there are errors, re-render the form with errors
        if errors:
            context = self.get_context_data()
            context['errors'] = errors
            context['form_data'] = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone_no': phone_no
            }
            return render(request, self.template_name, context)

        # If all validations pass, update fields and save
        user.first_name = first_name
        user.last_name = last_name
        user.save()  # Save to database

        # Redirect to account page or other page upon successful update
        return redirect('account')


class ChangePassword(TemplateView):
    template_name = 'account_change_password.html'

    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm()
        return self.render_to_response({'form': form})

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = self.request.user
            user.set_password(new_password)  # Set the new password
            user.save()

            # Keep the user logged in after changing the password
            update_session_auth_hash(request, user)

            # Redirect to the profile page or any other page
            return redirect('account')
        
        # If the form is invalid, re-render the page with form errors
        return self.render_to_response({'form': form})

class AddressDetail(TemplateView):
    template_name="account_address.html"