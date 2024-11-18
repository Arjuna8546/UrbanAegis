from django.shortcuts import render,redirect,get_object_or_404
from django.views.generic import TemplateView
from django.views import View
from core.models import *
from django.contrib import messages

class AddCart(TemplateView):
    template_name="account_cart.html"
    def post(self, request):
        product_id = request.POST.get('product_id')
        color = request.POST.get('color')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))  # Default to 1 if not specified

        if product_id and color and size:
            # Fetch the product variant based on color and size
            variant = get_object_or_404(ProductVariant, product_id=product_id, color=color, size=size)
            
            # Check if the user is authenticated
            if request.user.is_authenticated:
                # Handle cart for authenticated user
                cart_item, created = CartItem.objects.get_or_create(
                    user=request.user,
                    product=variant.product,
                    product_variant=variant,
                    defaults={'quantity': quantity},
                )
            else:
                # Handle cart for guest user
                session_id = request.session.session_key
                if not session_id:
                    request.session.create()  # Create session if it doesn't exist
                    session_id = request.session.session_key

                cart_item, created = CartItem.objects.get_or_create(
                    session_id=session_id,
                    product=variant.product,
                    product_variant=variant,
                    defaults={'quantity': quantity},
                )

            if not created:
                # If the item already exists, update the quantity
                cart_item.quantity += quantity
                cart_item.save()
                messages.success(request, f"Updated quantity for {variant.product.title} in your cart.")
            else:
                messages.success(request, f"Added {variant.product.title} to your cart.")
            
            return redirect('product_detail', product_id=product_id or 0)  # Redirect to the cart detail page

        # If no valid product_id, color, or size is provided, redirect to product detail with an error message
        messages.error(request, "Invalid product selection. Please try again.")
        return redirect('product_detail', product_id=product_id or 0) 