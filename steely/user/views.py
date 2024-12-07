from django.shortcuts import render,redirect,get_object_or_404,HttpResponse
from django.views.generic import TemplateView,ListView
from django.views import View
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from user.forms import PasswordChangeForm,UserAddressForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from core.models import UserAddress,Order,OrderItem,Wishlist
from django.db.models import Prefetch
from django.http import JsonResponse
from datetime import timedelta

class AccountDetail(TemplateView):
    template_name = 'account_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add the user to the context if they are authenticated
        if self.request.user.is_authenticated:
            context['user'] = self.request.user
        return context
    
    def post(self, request):
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_no = request.POST.get('phone_no')
        
        user = self.request.user
        errors = {}

        if not first_name:
            errors['first_name'] = "First name cannot be empty."
        if not last_name:
            errors['last_name'] = "Last name cannot be empty."

        if email:
            try:
                validate_email(email)
                user.email = email  
            except ValidationError:
                errors['email'] = "Invalid email format."
        else:
            errors['email'] = "Email cannot be empty."

        if phone_no and not phone_no.isdigit():
            errors['phone_no'] = "Phone number must contain only digits."
        else:
            user.phone_no = phone_no  

        if errors:
            context = self.get_context_data()
            context['errors'] = errors
            context['form_data'] = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone_no': phone_no
            }
            return render(request, self.template_name, context)

        user.first_name = first_name
        user.last_name = last_name
        user.save()  # Save to database

        return redirect('account')


class ChangePassword(TemplateView):
    template_name = 'account_change_password.html'

    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm()
        return self.render_to_response({'form': form})

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

class AddressDetail(TemplateView):
    template_name="account_address.html"

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
                    messages.success(request, "Address set as default.")
                else:
                    # Uncheck the default for this address
                    address.is_default = False
                    messages.info(request, "Default address removed.")

                address.save()

            except ValueError as e:
                messages.error(request, str(e))
        return redirect('addressdetail')
    
class UpdateAddress(View):
    def post(self,request,*args, **kwargs):
        address_id = request.POST.get("address_id")
        address = get_object_or_404(UserAddress, id=address_id, user=request.user)

        # Update the address details

        address.street_address = request.POST.get("street_address")
        address.city = request.POST.get("city")
        address.state = request.POST.get("state")
        address.pin_code = request.POST.get("zip_code")
        address.country = request.POST.get("country")
        
        address.save()

        messages.success(request, "Address updated successfully.")
        return redirect('addressdetail')

class DeleteAddress(View):
    def get(self,request,address_id):

        address= get_object_or_404(UserAddress,id=address_id)
        address.is_deleted=True
        address.save()
        return redirect('addressdetail')
    
class OrderListView(ListView):
    model = Order
    template_name = 'user_orderdetail.html'  # Update with your template path
    context_object_name = 'orders'
    paginate_by = 10  # Optional: Paginate the orders

    def get_queryset(self):
        user = self.request.user

        # Fetch orders for the logged-in user
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
            .order_by('-created_at')  # Show the latest orders first
        )
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
        "order_date": order.created_at.strftime("%d %b %Y"),
        "estimated_delivery": (order.created_at + timedelta(days=7)).strftime("%d %b %Y"),
        "total": order.total_amount,
        "discount":order.discount,
        "shipping_address": f"{order.address_id.street_address}, {order.address_id.city}, {order.address_id.state}, {order.address_id.country} Pin:{order.address_id.pin_code}",
        "status": order.status_of_order,
        "pay_method": order.payment_method,
        "pay_status": order.payment_status,
        "items": items,  # Include the list of order items
    }

    return JsonResponse(data)
class CancelOrder(View):
    def post(self, request, uuid):
        order = get_object_or_404(Order, uuid=uuid)

        # Example logic for cancelling an order
        if order.status_of_order not in ['Cancelled', 'Delivered']:
            order.status_of_order = 'Cancelled'
            order.save()

            # Return ordered quantity back to product variant
            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                product_variant = item.product_variant
                if product_variant:  # Ensure the product variant exists
                    product_variant.available_quantity += item.quantity
                    product_variant.save()

            messages.success(request,"order cannceled susscessfully")
        else:
            messages.error(request,"order canncelation failed")
        return redirect('userorderdetail')

class Wishlistview(View):

    def get(self,request):
        user=request.user
        wishlists= Wishlist.objects.filter(user=user.id)
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True) if request.user.is_authenticated else []
        
        
        return render(request,"wishlist.html",{'wishlists':wishlists,'user_wishlist':user_wishlist})