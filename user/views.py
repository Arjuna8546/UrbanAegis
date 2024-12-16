from django.conf import settings
from django.shortcuts import render,redirect,get_object_or_404,HttpResponse
from django.views.generic import TemplateView,ListView
from django.views import View
import re
import razorpay
from user.forms import PasswordChangeForm,UserAddressForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from core.models import UserAddress,Order,OrderItem,Wishlist,Wallet,WalletTransaction,ReturnRequest
from django.db.models import Prefetch
from django.http import JsonResponse
from datetime import timedelta
from django.db import transaction
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from django.template.loader import render_to_string
from weasyprint import HTML
import base64
from io import BytesIO
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json

class AccountDetail(LoginRequiredMixin, TemplateView):
    template_name = 'account_detail.html'
    login_url="login"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add the user to the context if they are authenticated
        if self.request.user.is_authenticated:
            context['user'] = self.request.user
        return context
    
    def post(self, request):
        first_name = request.POST.get('first_name', '').strip()  # Default to empty string to avoid None
        last_name = request.POST.get('last_name', '').strip()
        phone_no = request.POST.get('phone_no', '').strip()


        user = self.request.user
        errors = {}

        # Validation
        if not first_name:
            errors['first_name'] = "First name cannot be empty."
        if not last_name:
            errors['last_name'] = "Last name cannot be empty."
        
        PHONE_NUMBER_REGEX = r'^\d{10}$'

        if phone_no and not re.match(PHONE_NUMBER_REGEX, phone_no):
            errors['phone_no'] = "Enter a valid 10-digit phone number."

        if errors:
            context = self.get_context_data()
            context['errors'] = errors
            context['form_data'] = {
                'first_name': first_name,
                'last_name': last_name,
                'phone_no': phone_no
            }
            messages.error(request,"Error in updating Account details ")
            return render(request, self.template_name, context)

        # Update user details
        user.first_name = first_name
        user.last_name = last_name
        user.phone_no = phone_no
        user.save()  # Save to database

        messages.success(request,"Account details updated succsessfully")
        return redirect('account')



class ChangePassword(LoginRequiredMixin, TemplateView):
    template_name = 'account_change_password.html'
    login_url="login"

    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm()
        condition = request.user.is_google and not request.user.has_usable_password()
        return self.render_to_response({'form': form,'condition':condition})

    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = self.request.user
            user.set_password(new_password)  
            user.save()

            update_session_auth_hash(request, user)

            return redirect('account')

        return self.render_to_response({'form': form})

class AddressDetail(LoginRequiredMixin, TemplateView):
    template_name="account_address.html"
    login_url="login"

    def get(self,request,*args, **kwargs):
        form = UserAddressForm()
        addresses = UserAddress.objects.filter(user=request.user,is_deleted=False)
        return self.render_to_response({'form': form,'addresses': addresses})
    
    def post(self,request,*args, **kwargs):
        form = UserAddressForm(request.POST)
        if form.is_valid():
            street_address = form.cleaned_data['street_address']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            pincode = form.cleaned_data['pin_code']
            country = form.cleaned_data['country']

            # Check if the address already exists for the user
            address_exists = UserAddress.objects.filter(
                user=request.user,
                street_address=street_address,
                city=city,
                state=state,
                pin_code=pincode,
                country=country,
                is_deleted=False,  # Exclude soft-deleted addresses
            ).exists()

            if address_exists:
                messages.warning(request, "This address already exists.")
            else:
                address = form.save(commit=False)
                address.user = request.user  # Associate with the logged-in user
                address.save()
            
                messages.success(request, "Address added successfully.")
            return redirect('addressdetail')  # Redirect to profile or desired page
        else:
            messages.error(request, "Please correct the errors below.")
            return self.render_to_response({'form': form})
        
class SetAddressDefault(View):
    def post(self,request,address_id):

        if address_id:
            try:
                address = get_object_or_404(UserAddress, id=address_id, user=request.user)
        
                # Call the method to set the default address
                if "default_address" in request.POST:
                    # Set all other addresses as non-default
                    UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False)
                    
                    # Set the current address as default
                    address.is_default = True
                    messages.info(request, "Address set as default.")
                else:
                    # Uncheck the default for this address
                    address.is_default = False
                    messages.warning(request, "Default address removed.")

                address.save()

            except ValueError as e:
                messages.error(request, str(e))
        return redirect('addressdetail')
    
class UpdateAddress(View):
    def post(self, request, *args, **kwargs):
        address_id = request.POST.get("address_id")
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)

        # Bind the form with POST data and the existing address instance
        form = UserAddressForm(request.POST, instance=address)

        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully.")
            return redirect('addressdetail')
        else:
            # If form is invalid, render the same page with errors
            return render(request, 'account_address.html', {'form': form, 'address': address})

class DeleteAddress(View):
    def get(self,request,address_id):

        address= get_object_or_404(UserAddress,id=address_id)
        address.is_deleted=True
        address.save()
        return redirect('addressdetail')
    
class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'user_orderdetail.html'
    context_object_name = 'orders'
    paginate_by = 4  # Number of orders per page

    def get_queryset(self):
        """
        Fetch orders for the logged-in user, prefetch related data for optimization.
        """
        user = self.request.user
        return (
            Order.objects.filter(user=user)
            .prefetch_related(
                Prefetch(
                    'order_items',
                    queryset=OrderItem.objects.select_related('product_variant__product'),
                    to_attr='fetched_order_items'
                ),
                'address_id'
            )
            .order_by('-created_at')  # Latest orders first
        )

    def get_context_data(self, **kwargs):
        """
        Customize the context to include paginated orders manually.
        """
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        
        # Get page number from request
        page = self.request.GET.get('page', 1)
        
        # Paginate the queryset
        paginator = Paginator(queryset, self.paginate_by)
        try:
            orders = paginator.page(page)
        except PageNotAnInteger:
            orders = paginator.page(1)
        except EmptyPage:
            orders = paginator.page(paginator.num_pages)

        # Update context with paginated orders and paginator details
        context['orders'] = orders
        context['paginator'] = paginator
        context['is_paginated'] = orders.has_other_pages()
        return context

def order_details_api(request, uuid):
    order = get_object_or_404(Order, uuid=uuid, user=request.user)
    order_items = order.order_items.all()  # Fetch all related order items

    # Create a list of order item details
    items = [
        {
            "product_name": item.product_variant.product.title,
            "product_price": str(item.unit_price),
            "tax": str(item.tax),
            "quantity": item.quantity,
            "color": item.product_variant.color,
            "size": item.product_variant.size,
            "description": item.product_variant.product.description,
            "item_total":str(item.quantity*item.unit_price + item.tax)
        }
        for item in order_items
    ]

    # Add order-level details
    data = {
        "uuid": str(order.uuid),
        "order_id":str(order.order_id),
        "order_date": order.created_at.strftime("%d %b %Y"),
        "estimated_delivery": (order.created_at + timedelta(days=7)).strftime("%d %b %Y"),
        "total": str(order.total_amount),
        "discount": str(order.discount),
        "subtotal": str(order.subtotal),
        "shipping_address": f"{order.shipping_street}, {order.shipping_city}, {order.shipping_state}, {order.shipping_country}, PIN: {order.shipping_pincode}",
        "customer_email": order.customer_email,
        "customer_phone": order.customer_phone,
        "customer_name": order.customer_name,
        "status": order.status_of_order,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "items": items,  # Include the list of order items
    }

    return JsonResponse(data)
class CancelOrder(LoginRequiredMixin, View):
    login_url = 'login'

    def post(self, request, uuid):
        order = get_object_or_404(Order, uuid=uuid)

        try:
            with transaction.atomic():
                # Check if the order can be canceled
                if order.status_of_order not in ['Cancelled', 'Delivered']:
                    # Update the order status to 'Cancelled'
                    order.status_of_order = 'Cancelled'
                    order.save()

                    # Return ordered quantity back to product variant
                    order_items = OrderItem.objects.filter(order=order)
                    for item in order_items:
                        product_variant = item.product_variant
                        if product_variant:  # Ensure the product variant exists
                            product_variant.available_quantity += item.quantity
                            product_variant.save()

                    # Process refund to wallet for all paid orders
                    if order.payment_status == "paid":
                        # Refund the amount to wallet
                        wallet = Wallet.objects.get(user=order.user)
                        refund_amount = Decimal(order.total_amount)


                        # Add a transaction record for the refund
                        WalletTransaction.objects.create(
                            wallet=wallet,
                            amount=refund_amount,
                            transaction_type="CREDIT",
                            description=f"Refund for canceled order {order.uuid}"
                        )

                    messages.success(request, "Order canceled successfully. Refund processed to wallet.")
                else:
                    messages.error(request, "Order cannot be canceled.")
        except Exception as e:
            messages.error(request, f"Error while canceling the order: {str(e)}")
            return redirect('userorderdetail')

        return redirect('userorderdetail')

class WishlistView(LoginRequiredMixin, View):
    login_url = 'login'

    def get(self, request):
        user = request.user
        # Fetch the wishlist items for the logged-in user
        wishlists = Wishlist.objects.filter(user=user.id).filter(product__variants__is_delete=True,product__category__is_active=True).distinct('product') 
        user_wishlist = (
            Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
            if request.user.is_authenticated
            else []
        )

        # Serialize variants data for each product
        for wishlist_item in wishlists:
            variants = list(wishlist_item.product.variants.all().values('size', 'color'))
            wishlist_item.product.variants_json = json.dumps(variants)

        # Implement pagination
        page = request.GET.get('page', 1)  # Get the page number from the query string
        paginator = Paginator(wishlists, 4)  # Paginate with 4 items per page

        try:
            paginated_wishlists = paginator.page(page)
        except PageNotAnInteger:
            paginated_wishlists = paginator.page(1)
        except EmptyPage:
            paginated_wishlists = paginator.page(paginator.num_pages)

        # Render the template with paginated data
        return render(
            request,
            "wishlist.html",
            {
                'wishlists': paginated_wishlists,  # Pass the paginated wishlists
                'user_wishlist': user_wishlist,
            },
        )


    
@login_required
def download_invoice(request, uuid):
    # Get the order
    order = get_object_or_404(Order, uuid=uuid, user=request.user)
    
    try:
        # Generate barcode
        barcode_class = barcode.get_barcode_class('code128')
        barcode_instance = barcode_class(str(order.uuid), writer=ImageWriter())
        
        # Save barcode to BytesIO
        barcode_buffer = BytesIO()
        barcode_instance.write(barcode_buffer)
        
        # Convert barcode image to base64 for template
        barcode_image = base64.b64encode(barcode_buffer.getvalue()).decode()
        
        # Prepare context for template
        context = {
            'order': order,
            'barcode_image': barcode_image,
            'current_date': datetime.now().strftime('%d-%m-%Y')
        }
        
        # Generate HTML content
        html_content = render_to_string('invoice_template.html', context)
        
        # Create PDF using WeasyPrint
        pdf_buffer = BytesIO()
        HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf(pdf_buffer)
        
        # Create the HTTP response with PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Urban_Aegis_Invoice_{order.uuid}.pdf"'
        response.write(pdf_buffer.getvalue())
        
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating invoice: {str(e)}")
        return redirect('userorderdetail')
    
    finally:
        # Clean up resources
        if 'barcode_buffer' in locals():
            barcode_buffer.close()
        if 'pdf_buffer' in locals():
            pdf_buffer.close()



def ReturnOrder(request,uuid):
        order = get_object_or_404(Order, uuid=uuid, user=request.user)
        return render(request,"return_order_select.html",{'order':order})


def AddReturnOrder(request):
    
    if request.method == "POST":
        # Get the order UUID from the POST data
        order_uuid = request.POST.get("order_uuid")
        reason = request.POST.get("reason")
        selected_items = request.POST.getlist('return_items')

        # Retrieve the Order object using the UUID
        order = get_object_or_404(Order, uuid=order_uuid)

        # Loop through the selected items and create ReturnRequest instances
        for item_id in selected_items:
            # Get the OrderItem instance based on the ID
            order_item = get_object_or_404(OrderItem, id=item_id)

            if ReturnRequest.objects.filter(orderItem=order_item).exists():
                # If it exists, skip and return a message to the user
                messages.warning(request, f"Return request for item {order_item.product_variant.product.title} is already submitted and is processing.")
                continue  # Skip to the next item

            # Create a new ReturnRequest instance
            return_request = ReturnRequest(
                order=order,
                orderItem=order_item,
                user=request.user,
                reason=reason
            )
            return_request.save()

        # Redirect or render a success response
        messages.success(request, "Returning submitted successfully. Prossessing")
        return redirect('userorderdetail')  # Replace with your desired URL name or template
    

    # Handle the case for GET request if needed
    messages.success(request, "Some issue while submitting Return")
    return redirect('userorderdetail')


class ReturnOrderView(LoginRequiredMixin,View):
    login_url = 'login'  # Specify the login URL
    

    def get(self,request):
        user=request.user
        retrunorder=ReturnRequest.objects.filter(user=user)

        context={
            "return_orders":retrunorder,
        }
        return render(request,"account_order_return.html",context)
def completepayment(request,uuid):

    order = get_object_or_404(Order,uuid=uuid)
    total = order.total_amount
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    payment_amount = int(float(total) * 100)  # Convert to paise
    print(payment_amount)
    
    # Create Razorpay order
    razorpay_order = client.order.create({
        'amount': payment_amount,
        'currency': 'INR',
        'payment_capture': '1'
    })
    
    # Update order with razorpay_order_id
    order.razorpay_order_id = razorpay_order['id']
    order.save()
    context = {
        'order_id': razorpay_order['id'],
        'total': total,
        'amount': payment_amount,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'user': request.user
    }
    
    return render(request, 'razorpay_checkout.html', context)
    