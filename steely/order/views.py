from django.shortcuts import render
from django.views.generic import TemplateView
from django.views import View
from core.models import *

class Checkout(View):
    def get(self, request):
        user = request.user
        
        # Fetch cart items for the logged-in user
        cartitems = CartItem.objects.filter(user=user)

                # Calculate subtotal
        subtotal = float(sum(item.product_variant.price * item.quantity for item in cartitems))
        
        # Define tax rate (e.g., 10%)
        tax_rate = 0.05
        tax = round(subtotal * tax_rate, 2)
        
        # Calculate total
        total = subtotal + tax
        
        # Fetch addresses for the logged-in user
        addresses = UserAddress.objects.filter(user=user, is_deleted=False)
        
        context = {
            "user":user,
            "cartitems": cartitems,
            "addresses": addresses,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }

        return render(request, "checkout.html", context)
    
