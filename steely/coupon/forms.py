from django import forms
from core.models import Coupon

class CouponForm(forms.ModelForm):
    valid_from = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'id': 'valid_from',
            'class': 'form-control'
        }),
        help_text='Select the start date and time'
    )
    valid_until = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'id': 'valid_until',
            'class': 'form-control'
        }),
        help_text='Select the end date and time'
    )

    class Meta:
        model = Coupon
        fields = [
            'code', 'discount_type', 'discount_value', 'min_purchase',
            'valid_from', 'valid_until', 'usage_limit', 'status', 'description'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter coupon code',
                'id': 'coupon_code'
            }),
            'discount_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'discount_type'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'discount_value'
            }),
            'min_purchase': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'id': 'min_purchase'
            }),
            'usage_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'usage_limit'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'id': 'status'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'id': 'description'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        discount_type = cleaned_data.get('discount_type')
        discount_value = cleaned_data.get('discount_value')

        if valid_from and valid_until and valid_from >= valid_until:
            raise forms.ValidationError("End date must be after start date.")

        if discount_type == 'percentage' and discount_value > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
