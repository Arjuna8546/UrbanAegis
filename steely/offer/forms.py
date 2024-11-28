from django import forms
from core.models import Product,Category,Offer

class OfferForm(forms.ModelForm):

    valid_from = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    valid_until = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_delete=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    discount_type = forms.ChoiceField(
        choices=Offer.DISCOUNT_TYPE_CHOICE,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    discount_value = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=Offer.STATUS_CHOICE,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    class Meta:
        model = Offer
        fields = ['discount_type','discount_value','valid_from','valid_until','status','description','product','category']


    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        category = cleaned_data.get('category')
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')

        if not product and not category:
            raise forms.ValidationError('Please select either a product or category')
        
        if product and category:
            raise forms.ValidationError('Please select either a product or category, not both')
        
        if valid_from and valid_until and valid_from >= valid_until:
            raise forms.ValidationError('Valid from date must be before valid until date')
    