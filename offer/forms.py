from django import forms
from core.models import Product,Category,Offer

class OfferForm(forms.ModelForm):


    
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
        fields = ['discount_type','discount_value','status','description','product','category']


    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        category = cleaned_data.get('category')


        if not product and not category:
            raise forms.ValidationError('Please select either a product or category')
        
        if product and category:
            raise forms.ValidationError('Please select either a product or category, not both')
        

        
        instance_id = self.instance.id if self.instance else None
        
        if category:
            overlapping_category_offers = Offer.objects.filter(
                category=category,

            ).exclude(id=instance_id)
            if overlapping_category_offers.exists():
                raise forms.ValidationError(f'An offer for the category "{category}" already exists in this period.')

        if product:
            overlapping_product_offers = Offer.objects.filter(
                product=product,

            ).exclude(id=instance_id)
            if overlapping_product_offers.exists():
                raise forms.ValidationError(f'An offer for the product "{product}" already exists in this period.')
        return cleaned_data
    