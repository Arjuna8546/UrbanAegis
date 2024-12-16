import json
from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
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
from django.contrib.auth.mixins import  UserPassesTestMixin
from decimal import Decimal
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


class Checkout(LoginRequiredMixin, View):
    login_url = '/login/'  # Redirect to the login page if not logged in
    redirect_field_name = 'home'  # Redirect back to the intended page after login

    def get(self, request):
        user = request.user
        cartitems = CartItem.objects.filter(user=user,product__category__is_active=True)


        for item in cartitems:
            if item.product_variant.is_delete is False:
                # Remove the item from the cart
                item.delete()
            if item.quantity > item.product_variant.available_quantity:
                messages.error(
                    request, 
                    f"The item '{item.product_variant.product.title}' in your cart is out of stock."
                )
                return redirect('addcart')  # Redirect to the cart page with an error messag

        
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
        wallet = Wallet.objects.get(user=user)

        
        context = {
            "user": user,
            "cartitems": cartitems,
            "addresses": addresses,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "wallet":wallet
        }

        return render(request, "checkout.html", context)
    

class OrderAdd(LoginRequiredMixin,View):
    login_url="login"

    def post(self, request):
        user = request.user
        cart_items = CartItem.objects.filter(user=user,product__category__is_active=True).select_related('product_variant')  # Optimize query with select_related
        # Calculate subtotal with offer discounts
        subtotal = 0
        valid_cart_items = []
        for item in cart_items:
            if item.product_variant.is_delete is False:
                item.delete()
            else:
                valid_cart_items.append(item)
        
        for item in valid_cart_items:
            item_price = item.product_variant.price
            if item.product_variant.is_offer:
                item_price = item_price - item.product_variant.offer_discount
            subtotal += float(item_price * item.quantity)
        tax_rate = 0.05
        tax = round(subtotal * tax_rate, 2)
        total = subtotal + tax
        subtotal=total
        payment_method = request.POST.get("payment_method")
        address_id = request.POST.get('address')
        discount1 = request.POST.get('discount', '0')
        total1 = request.POST.get('total', '0')
        
        if total1:
            
            total=float(total1)
            
        if not discount1:
            discount1=0.00
        if not payment_method:
            messages.error(request, "Please select a payment method.")
            return redirect("checkout")
        if not valid_cart_items:
            messages.error(request, "No valid items to purchase. Please check your cart and try again.")
            return redirect('checkout')
        
        if payment_method.lower() == 'cod' and total>1000:
            messages.error(request, "Cash On Delivery is not available for Order above 1000.")
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
                if payment_method.lower() == "wallet":
                    wallet = Wallet.objects.get(user=user)

                    if wallet.balance >= Decimal(total):
                        


                        # Create the order
                        order = Order.objects.create(
                            user=user,
                            address_id=address,
                            customer_email=user.email,
                            customer_phone=user.phone_no,
                            customer_name=f"{user.first_name} {user.last_name}",
                            shipping_street=address.street_address,
                            shipping_city=address.city,
                            shipping_state=address.state,
                            shipping_pincode=address.pin_code,
                            shipping_country=address.country,
                            subtotal=subtotal,
                            total_amount=total,
                            payment_method=payment_method,
                            discount=discount1,
                            payment_status="paid"
                        )

                        # Add a wallet transaction record
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=total,
                            transaction_type="DEBIT",
                            description="Order Payment"
                        )

                        order_items = []
                        for item in valid_cart_items:
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

                        messages.success(request, "Order placed successfully using Wallet!")
                        return render(request, 'order_sucsses.html', {'order': order})
                    else:
                        messages.error(request, "Insufficient wallet balance to complete the order.")
                        return redirect("checkout")
                # Create the order
                order = Order.objects.create(
                    user=user,
                    address_id=address,
                    customer_email=user.email,
                    customer_phone=user.phone_no,  # Adjust based on how you store phone numbers
                    customer_name=f"{user.first_name} {user.last_name}",
                    shipping_street=address.street_address,
                    shipping_city=address.city,
                    shipping_state=address.state,
                    shipping_pincode=address.pin_code,
                    shipping_country=address.country,
                    subtotal= subtotal,
                    total_amount=total,
                    payment_method=payment_method,
                    discount = discount1,
                    payment_status = "pending"


                )
                # Create order items
                order_items = []
                for item in valid_cart_items:
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
                    if payment_method.lower() == 'cod':
                        product_variant.available_quantity = F('available_quantity') - item.quantity
                        product_variant.save()

                        

                OrderItem.objects.bulk_create(order_items)  # Use bulk_create for efficiency


                # Clear the user's cart after successful order creation
                

                if payment_method.lower() == 'cod':
                    cart_items.delete()
                    messages.success(request, "Order placed successfully!")
                    return render(request, 'order_sucsses.html', {'order': order})
                elif payment_method.lower() == 'razorpay':  # Razorpay payment
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    payment_amount = int(float(total) * 100)  # Convert to paise
                    
                    # Create Razorpay order
                    razorpay_order = client.order.create({
                        'amount': payment_amount,
                        'currency': 'INR',
                        'payment_capture': '1'
                    })
                    
                    # Update order with razorpay_order_id
                    order.razorpay_order_id = razorpay_order['id']
                    order.payment_status="failed"
                    order.save()

                    context = {
                        'order_id': razorpay_order['id'],
                        'total': total,
                        'amount': payment_amount,
                        'razorpay_key': settings.RAZORPAY_KEY_ID,
                        'user': request.user
                    }
                    
                    return render(request, 'razorpay_checkout.html', context)
                
                      
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("checkout")
    
    
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
        tax = Decimal('0.05') * subtotal
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



@login_required
@require_POST
def verify_payment(request):
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Get payment verification data
    payment_id = request.POST.get('razorpay_payment_id')
    order_id = request.POST.get('razorpay_order_id')
    signature = request.POST.get('razorpay_signature')
    
    try:
        # Verify the payment signature
        params_dict = {
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        # Update order payment status
        order = Order.objects.get(razorpay_order_id=order_id)
        order.payment_status = 'paid'
        order.payment_method = 'RazorPay'
        order.razorpay_payment_id = payment_id
        order.razorpay_signature_id = signature
        order.save()
        
        cart_items = CartItem.objects.filter(user=request.user)
        for item in cart_items:
            product_variant = item.product_variant
            product_variant.available_quantity = F('available_quantity') - item.quantity
            product_variant.save()

        # Clear the cart after the order is completed
        cart_items.delete()
        
        messages.success(request, "Payment successful! Your order has been confirmed.")
        return render(request, 'order_sucsses.html', {'order': order})
        
    except razorpay.errors.SignatureVerificationError:
        print("payment failed")
        messages.error(request, "Payment verification failed. Please contact support.")
        return redirect('checkout')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('checkout')


def check_user_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        password = data.get('password')

        try:
            user = request.user

            if user.is_google==True and user.has_usable_password()==False:
                    return JsonResponse({
                        'success': True,
                        'message': 'The user has a usable password.',
                    })
                

            # Check if the password is correct
            if user.check_password(password):
                return JsonResponse({
                    'success': True,
                    'message': 'Password is correct.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Password is incorrect.'
                })
        except Users.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'No account found with this email address.'
            })
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

class StaffRequiredMixin(UserPassesTestMixin):
    login_url = 'admin_login'  # URL to redirect unauthorized users to

    def test_func(self):
        return self.request.user.is_staff
    
class OrderReturnAdminView(StaffRequiredMixin,View):
    def get(self,request):
        order_list = ReturnRequest.objects.all().order_by('-id')
        paginator = Paginator(order_list, 10)  # Show 10 returns per page
        page = request.GET.get('page')
        try:
            orders = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            orders = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results
            orders = paginator.page(paginator.num_pages)
        return render(request, 'admin_order_return.html', {'returns': orders})
def updatereturnstatus(request):
    try:
        if request.method=="POST":
            data = json.loads(request.body)

            status = data.get('status')
            return_id = data.get('returnId')
            
            if not return_id or not status:
                    return JsonResponse({'success': False, 'error': 'Missing returnId or status'}, status=400)
            try:
                    return_order=get_object_or_404(ReturnRequest,id=return_id)
                    return_order.status = status
                    return_order.save()
                    return JsonResponse({'success': True, 'message': 'Status updated successfully'})
            except ReturnRequest.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Return request not found'}, status=404)
    except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

def updateReturnReceived(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)

            # Extract returnId and received status
            return_id = data.get('returnId')
            received = data.get('received')

            # Validate inputs
            if return_id is None or received is None:
                return JsonResponse({'success': False, 'error': 'Missing returnId or received status'}, status=400)

            # Get the return order and update its status
            return_order = get_object_or_404(ReturnRequest, id=return_id)
            return_order.return_received = received
            return_order.save()

            return JsonResponse({'success': True, 'message': 'Product received at warehouse successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON body'}, status=400)

    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)