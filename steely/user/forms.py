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
    print(new_password)
    
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

    def __init__(self, *args, **kwargs):
        super(UserAddressForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['required'] = 'true'
