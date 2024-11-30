import json
from django.http import JsonResponse
from django.shortcuts import render,redirect
from django.views.generic import TemplateView
from django.views import View
from core.models import *
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.db.models import F
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal


class Checkout(LoginRequiredMixin, View):
    login_url = '/login/'  # Redirect to the login page if not logged in
    redirect_field_name = 'home'  # Redirect back to the intended page after login

    def get(self, request):
        user = request.user
        cartitems = CartItem.objects.filter(user=user)

        
        # Calculate subtotal, tax, and total with offer discounts
        subtotal = 0
        for item in cartitems:
            item_price = item.product_variant.price
            if item.product_variant.is_offer:
                item_price = item_price - item.product_variant.offer_discount
            subtotal += item_price * item.quantity
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
        # Calculate subtotal with offer discounts
        subtotal = 0
        for item in cart_items:
            item_price = item.product_variant.price
            if item.product_variant.is_offer:
                item_price = item_price - item.product_variant.offer_discount
            subtotal += float(item_price * item.quantity)
        tax_rate = 0.05
        tax = round(subtotal * tax_rate, 2)
        total = subtotal + tax
        payment_method = request.POST.get("payment_method")
        address_id = request.POST.get('address')
        discount1 = request.POST.get('discount', '0')
        total1 = request.POST.get('total', '0')
        if total1:
            total=total1
        if not discount1:
            discount1=0.00
        if payment_method =='RazorPay':
            payment_status="Paid"

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
                    subtotal= subtotal,
                    total_amount=total,
                    payment_method=payment_method,
                    discount = discount1,
                    payment_status=payment_status

                )
                # Create order items
                order_items = []
                for item in cart_items:
                    product_variant = item.product_variant

                    # Check stock availability
                    if product_variant.available_quantity < item.quantity:
                        raise ValueError(f"Insufficient stock for {product_variant.product.title}")

                    tax_rate = Decimal('0.05')
                    
                     # Create OrderItem
                    unit_price = product_variant.price
                    if product_variant.is_offer:
                        unit_price = unit_price - product_variant.offer_discount
                    
                    item_total = unit_price * item.quantity
                    item_tax = (item_total * tax_rate).quantize(Decimal('0.01'))
                    
                    order_items.append(OrderItem(
                        order=order,
                        product_variant=product_variant,
                        quantity=item.quantity,
                        unit_price=unit_price,
                        total_price=item_total + item_tax,
                        tax=item_tax
                    ))

                    # Update stock
                    product_variant.available_quantity = F('available_quantity') - item.quantity
                    product_variant.save()

                OrderItem.objects.bulk_create(order_items)  # Use bulk_create for efficiency


                # Clear the user's cart after successful order creation
                cart_items.delete()

                if payment_method == 'RazorPay':
                        return JsonResponse({
                            'status': 'success',
                            'order_id': order.id,
                            'total_amount': float(total),
                            # Add this line
                    })
               


        except ValueError as e:
            print("error")
            messages.error(request, str(e))
            return redirect("checkout")  # Redirect to retry checkout in case of errors

        messages.success(request, "Order placed successfully!")
        return redirect("order_sucsses")
    
@login_required
@require_POST
def apply_coupon(request):
    import json
    from decimal import Decimal
    from django.utils import timezone

    try:
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code')

        if not coupon_code:
            return JsonResponse({
                'valid': False,
                'message': 'Please enter a coupon code.'
            })

        try:
            coupon = Coupon.objects.get(code=coupon_code)
            
        except Coupon.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid coupon code.'
            })

        # Get cart total
        cart_items = CartItem.objects.filter(user=request.user)
        subtotal = sum(item.get_total_price() for item in cart_items)

        # Validate coupon
        if not coupon.is_active():

            return JsonResponse({
                'valid': False,
                'message': 'This coupon has expired.'
            })

        can_use, message = coupon.can_use(request.user, subtotal)
        print(can_use)

        if not can_use:
            return JsonResponse({
                'valid': False,
                'message': message,
            })
        # Calculate discount
        discount = coupon.calculate_discount(subtotal)
        
        # Calculate new total
        total = subtotal - discount

        # Add tax calculation (assuming 18% GST)
        tax = Decimal('0.05') * total
        final_total = total + tax

        # Mark coupon as used
        # coupon.use(request.user)

        # Store coupon in session for order processing
        request.session['applied_coupon'] = coupon.code

        return JsonResponse({
            'valid': True,
            'message': 'Coupon applied successfully!',
            'subtotal': str(subtotal),
            'discount': str(discount),
            'tax': str(tax),
            'total': str(final_total)
        })

    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': 'An error occurred while applying the coupon.'
        })
@login_required
@require_POST
def remove_coupon(request):
    # Remove coupon from session
    if 'applied_coupon' in request.session:
        del request.session['applied_coupon']

    # Calculate normal totals
    cart_items = CartItem.objects.filter(user=request.user)
    subtotal = sum(item.get_total_price() for item in cart_items)
    tax = Decimal('0.05') * subtotal
    total = subtotal + tax

    return JsonResponse({
        'valid': True,
        'message': 'Coupon removed successfully!',
        'subtotal': str(subtotal),
        'tax': str(tax),
        'total': str(total)
    })

def create_order(request):
    if request.method == 'POST':
        try:
            # Get the amount and clean it
            amount_str = request.POST.get('amount', '0')
            # Remove any currency symbols, commas, and whitespace
            amount_str = amount_str.replace('₹', '').replace(',', '').strip()
            # Convert to float first to handle decimal points
            amount_float = float(amount_str)
            # Convert to paise (multiply by 100)
            amount_paise = int(amount_float * 100)

            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payment = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'payment_capture': '1'
            })
            return JsonResponse({
                'order_id': payment['id'],
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'amount': amount_paise,
            })
        except (ValueError, Decimal.ConversionSyntax) as e:
            print(f"Error processing amount: {str(e)}")
            return JsonResponse({
                'error': 'Invalid amount format'
            }, status=400)
        except Exception as e:
            print(f"Error creating order: {str(e)}")
            return JsonResponse({
                'error': str(e)
            }, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def verify_payment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # print("Payment verification data:", data)
        payment_id = data.get('razorpay_payment_id')
        order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')
        
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Verify the payment signature
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            })
            # Payment verified, update the order in the database
            # Example: Mark order as paid
            # order = Order.objects.get(id=order_id)
            # order.payment_id = payment_id
            # order.status = "Paid"
            # order.save()

            return JsonResponse({'success': True, 'message': 'Payment verified successfully.'})

        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'success': False, 'message': 'Payment verification failed.'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    
class order_succsess(TemplateView):
    template_name="order_sucsses.html"





        
    
