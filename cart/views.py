from django.shortcuts import render,redirect,get_object_or_404
from django.views.generic import TemplateView
from django.views import View
from core.models import *
from django.contrib import messages
from django.http import JsonResponse
import json
from django.contrib.auth.mixins import LoginRequiredMixin

class AddCart(LoginRequiredMixin, TemplateView):
    template_name="account_cart.html"
    login_url="login"
    def get(self,request):
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user,product__category__is_active=True)
        else:
            session_id = request.session.session_key
            cart_items = CartItem.objects.filter(session_id=session_id)
        
        for item in cart_items:
            if item.product_variant.is_delete is False:
                # Remove the item from the cart
                item.delete()
        
        

        # Format cart data for frontend
        cart_data = [
            {
                'id': item.id,
                'name': item.product.title,
                'price': float(item.get_price()),
                'color': item.product_variant.color if item.product_variant else None,
                'size': item.product_variant.size if item.product_variant else None,
                'quantity': item.quantity,
                'image': item.product.product_images.first().image_url if item.product.product_images.exists() else '/placeholder.svg',
                'stock': item.product_variant.available_quantity 

            }
            for item in cart_items
        ]

        
        
        context = {
            'cart_data': cart_data,
            'tax_rate': 0.05  # Pass tax rate if needed
            
        }
        return render(request, 'account_cart.html', context)
    
    def post(self, request):
        product_id = request.POST.get('product_id')
        color = request.POST.get('color')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))  # Default to 1 if not specified

        if product_id and color and size:
            # Fetch the product variant based on color and size
            variant = get_object_or_404(ProductVariant, product_id=product_id, color=color, size=size)

            if variant.available_quantity>=quantity:
                
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
            else:
                messages.error(request, f" {variant.product.title} out of stock.")
            
            return redirect('product_detail', product_id=product_id or 0)  # Redirect to the cart detail page

        # If no valid product_id, color, or size is provided, redirect to product detail with an error message
        messages.error(request, "Invalid product selection. Please try again.")
        return redirect('product_detail', product_id=product_id or 0) 
    

def remove_cart_item(request, id):
    if request.method == 'POST':  # Ensure only POST requests are allowed
        try:
            if request.user.is_authenticated:
                # For authenticated users, retrieve the cart item for the logged-in user
                cart_item = get_object_or_404(CartItem, id=id, user=request.user)
            else:
                # For guest users, use the session ID to identify their cart
                session_id = request.session.session_key
                if not session_id:
                    return JsonResponse({'success': False, 'message': 'Session not found'}, status=400)

                cart_item = get_object_or_404(CartItem, id=id, session_id=session_id)

            cart_item.delete()  # Remove the item from the database
            return JsonResponse({'success': True, 'message': 'Item removed successfully'})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def update_cart_item_quantity(request, id):
    if request.method == 'POST':
        try:
            # Parse JSON body
            data = json.loads(request.body.decode('utf-8'))
            new_quantity = data.get('quantity')

            if not new_quantity or new_quantity <= 0:
                return JsonResponse({'success': False, 'message': 'Quantity must be greater than 0'}, status=400)

            if request.user.is_authenticated:
                # For authenticated users, retrieve the cart item for the logged-in user
                cart_item = get_object_or_404(CartItem, id=id, user=request.user)
            else:
                # For guest users, use the session ID to identify their cart
                session_id = request.session.session_key
                if not session_id:
                    return JsonResponse({'success': False, 'message': 'Session not found'}, status=400)

                cart_item = get_object_or_404(CartItem, id=id, session_id=session_id)

            available_stock = cart_item.product_variant.available_quantity 
            # Update the quantity
            if new_quantity > available_stock:
                return JsonResponse({
                    'success': False,
                    'message': f"Only {available_stock} items available in stock.",
                }, status=400)

            cart_item.quantity = new_quantity
            cart_item.save()

            return JsonResponse({
                'success': True,
                'message': 'Quantity updated successfully',
                'quantity': cart_item.quantity
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cart item not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def add_to_cart_modal(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else request.POST
            product_id = data.get('product_id')
            color = data.get('color')
            size = data.get('size')
            quantity = int(data.get('quantity', 1))

            if not all([product_id, color, size]):
                return JsonResponse({
                    'success': False,
                    'message': "Please select size and color"
                }, status=400)

            try:
                variant = ProductVariant.objects.get(
                    product_id=product_id, 
                    color=color, 
                    size=size
                )
            except ProductVariant.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': "Selected variant is not available"
                }, status=404)

            if variant.available_quantity < quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Only {variant.available_quantity} items available in stock"
                }, status=400)
            
            if request.user.is_authenticated:
                cart_item, created = CartItem.objects.get_or_create(
                    user=request.user,
                    product=variant.product,
                    product_variant=variant,
                    defaults={'quantity': quantity},
                )
            else:
                session_id = request.session.session_key
                if not session_id:
                    request.session.create()
                    session_id = request.session.session_key

                cart_item, created = CartItem.objects.get_or_create(
                    session_id=session_id,
                    product=variant.product,
                    product_variant=variant,
                    defaults={'quantity': quantity},
                )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                message = f"Updated quantity for {variant.product.title} in your cart"
            else:
                message = f"Added {variant.product.title} to your cart"

            return JsonResponse({
                'success': True,
                'message': message,
                'cart_item': {
                    'id': cart_item.id,
                    'product_name': variant.product.title,
                    'quantity': cart_item.quantity,
                    'color': variant.color,
                    'size': variant.size,
                    'price': str(variant.price)
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': "Invalid request method"
    }, status=405)