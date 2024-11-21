from django.shortcuts import render,redirect
from django.views.generic import TemplateView
from django.views import View
from core.models import *
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.db.models import F
from django.contrib.auth.mixins import LoginRequiredMixin

class Checkout(LoginRequiredMixin, View):
    login_url = '/login/'  # Redirect to the login page if not logged in
    redirect_field_name = 'home'  # Redirect back to the intended page after login

    def get(self, request):
        user = request.user
        cartitems = CartItem.objects.filter(user=user)
        
        # Calculate subtotal, tax, and total
        subtotal = sum(item.product_variant.price * item.quantity for item in cartitems)
        tax_rate = Decimal('0.05')
        tax = round(subtotal * tax_rate, 2)
        total = subtotal + tax
        
        # Fetch addresses for the user
        addresses = UserAddress.objects.filter(user=user, is_deleted=False)
        
        context = {
            "user": user,
            "cartitems": cartitems,
            "addresses": addresses,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }

        return render(request, "checkout.html", context)
    

class OrderAdd(View):
    def post(self, request):
        user = request.user
        cart_items = CartItem.objects.filter(user=user).select_related('product_variant')  # Optimize query with select_related
        subtotal = float(sum(item.product_variant.price * item.quantity for item in cart_items))
        tax_rate = 0.05
        tax = round(subtotal * tax_rate, 2)
        total = subtotal + tax
        payment_method = request.POST.get("payment_method")
        address_id = request.POST.get('address')

        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect("checkout")

        try:
            address = UserAddress.objects.get(id=address_id, user=user)
        except UserAddress.DoesNotExist:
            messages.error(request, "Invalid address selected.")
            return redirect("checkout")  # Redirect to checkout for the user to try again

        if not cart_items.exists():
            messages.error(request, "Your cart is empty.")
            return redirect("checkout")  # Redirect to the cart page

        try:
            with transaction.atomic():
                # Create the order
                order = Order.objects.create(
                    user=user,
                    address_id=address,
                    total_amount=total,
                    payment_method=payment_method,
                )
                # Create order items
                order_items = []
                for item in cart_items:
                    product_variant = item.product_variant

                    # Check stock availability
                    if product_variant.available_quantity < item.quantity:
                        raise ValueError(f"Insufficient stock for {product_variant.name}")

                    tax_rate = Decimal('0.05')
                    # Create OrderItem
                    order_items.append(OrderItem(
                        order=order,
                        product_variant=product_variant,
                        quantity=item.quantity,
                        unit_price=product_variant.price,
                        total_price=(product_variant.price * item.quantity) + 
                                    (product_variant.price * item.quantity * tax_rate).quantize(Decimal('0.01')),
                        tax=(product_variant.price * item.quantity * tax_rate).quantize(Decimal('0.01'))
                    ))

                    # Update stock
                    product_variant.available_quantity = F('available_quantity') - item.quantity
                    product_variant.save()

                OrderItem.objects.bulk_create(order_items)  # Use bulk_create for efficiency


                # Clear the user's cart after successful order creation
                cart_items.delete()

        except ValueError as e:
            messages.error(request, str(e))
            return redirect("checkout")  # Redirect to retry checkout in case of errors

        messages.success(request, "Order placed successfully!")
        return redirect("addcart")


        
    
