import re
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from core.models import UserAddress

class PasswordChangeForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'new-password'}),
        validators=[validate_password],  # Apply Django's built-in password validators
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'confirm-password'}),
        label="Confirm Password"
    )

    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data
    
class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = ['street_address', 'city', 'state', 'pin_code', 'country']
        widgets = {
            'street_address': forms.TextInput(attrs={
                'class': 'am-input',
                'id': 'shipping-street',
                'placeholder': 'Street Address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'am-input',
                'id': 'shipping-city',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'am-input',
                'id': 'shipping-state',
                'placeholder': 'State'
            }),
            'pin_code': forms.TextInput(attrs={
                'class': 'am-input',
                'id': 'shipping-pincode',
                'placeholder': 'Pin Code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'am-input',
                'id': 'shipping-country',
                'placeholder': 'Country'
            }),
        }

    
    def clean_pin_code(self):
        """Validate pin code for exactly 6 digits (India example)"""
        pin_code = self.cleaned_data.get('pin_code', '').strip()
        if pin_code and not re.match(r'^\d{6}$', pin_code):
            raise ValidationError("Pin Code must be exactly 6 digits.")
        return pin_code

    def clean_city(self):
        """Ensure city contains only letters and spaces"""
        city = self.cleaned_data.get('city', '').strip()
        if city and not re.match(r'^[a-zA-Z\s\-]+$', city):
            raise ValidationError("City name must contain only letters and spaces.")
        return city

    def clean_state(self):
        """Ensure state contains only letters and spaces"""
        state = self.cleaned_data.get('state', '').strip()
        if state and not re.match(r'^[a-zA-Z\s\-]+$', state):
            raise ValidationError("State name must contain only letters and spaces.")
        return state

    def clean_country(self):
        """Ensure country is valid"""
        country = self.cleaned_data.get('country', '').strip()
        if not country:
            raise ValidationError("Country is required.")
        return country

    def clean_street_address(self):
        """Ensure street address is not empty"""
        street_address = self.cleaned_data.get('street_address', '').strip()
        if street_address and len(street_address) > 255:
            raise ValidationError("Street Address cannot exceed 255 characters.")
        return street_address

    def clean(self):
        """Custom overall validation if needed"""
        cleaned_data = super().clean()

        # Example: Ensure pin_code matches country-specific rules
        country = cleaned_data.get('country')
        pin_code = cleaned_data.get('pin_code')

        if country == "India" and pin_code and not re.match(r'^\d{6}$', pin_code):
            self.add_error('pin_code', "For India, Pin Code must be exactly 6 digits.")

        return cleaned_data