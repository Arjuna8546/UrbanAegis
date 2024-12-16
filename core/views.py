from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.views import View
from core.models import Users,Product, ProductVariant, ProductImage,Category,Wishlist,Offer
from random import randint
from django.contrib.auth import authenticate, login,logout
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Min
from core.forms import RegisterForm
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.template.loader import render_to_string
from django.db.models import Count


class RegisterView(View):
    def get(self, request):
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():

            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            request.session['user_data'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password
            }

            self.generate_and_send_otp(email, request)

            return redirect('verifyotp')

        return render(request, 'register.html', {'form': form})

    def generate_and_send_otp(self, email, request):
        otp = randint(100000, 999999)  
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        send_mail(
            'Your OTP Code',
            f'Your OTP is {otp}. It is valid for 5 minutes.',
            'your_email@example.com',
            [email],
            fail_silently=False,
        )
        messages.info(request, f'OTP sent to {email}. Please verify.')

class VerifyOTPView(View):
    def get(self, request):
        return render(request, 'verify_otp.html')

    def post(self, request):
        # Check which button was clicked
        if 'verify_otp' in request.POST:
            return self.verify_otp_func(request)
        elif 'resend_otp' in request.POST:
            self.generate_and_send_otp(request)
            messages.info(request, "A new OTP has been sent to your email.")
            return redirect('verifyotp')

    def verify_otp_func(self, request):
        otp_entered = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        otp_generated_at_str = request.session.get('otp_generated_at')

        # Check if OTP is available and retrieve generation time
        if stored_otp and otp_generated_at_str:
            otp_generated_at = timezone.datetime.fromisoformat(otp_generated_at_str)
            expiration_time = otp_generated_at + timedelta(minutes=5)

            # Validate OTP within 5 minutes
            if timezone.now() <= expiration_time:
                if str(stored_otp) == otp_entered:
                    user_data = request.session.pop('user_data')
                    user = Users.objects.create_user(
                        email=user_data['email'],
                        first_name=user_data['first_name'],
                        last_name=user_data['last_name'],
                        password=user_data['password'],
                        join_date=timezone.now(),
                    )
                    user.is_active = True
                    user.save()

                    # Clear OTP from session
                    request.session.pop('otp', None)
                    request.session.pop('otp_generated_at', None)

                    messages.success(request, "OTP verified successfully! Your account has been created.")
                    return redirect('login')
                else:
                    messages.error(request, "Invalid OTP. Please try again.")
            else:
                messages.error(request, "OTP has expired. Please request a new OTP.")
                return redirect('verifyotp')

        return render(request, 'verify_otp.html')

    def generate_and_send_otp(self, request):
        otp = randint(100000, 999999)
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        email = request.session['user_data']['email']
        send_mail(
            'Resend OTP Code',
            f'Your OTP is {otp}. It is valid for 5 minutes.',
            'your_email@example.com',
            [email],
            fail_silently=False,
        )
        


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context['user'] = self.request.user
            # Add user wishlist to context
            context['user_wishlist'] = Wishlist.objects.filter(
                user=self.request.user
            ).values_list('product_id', flat=True)
        else:
            context['user_wishlist'] = [] 

        products = Product.objects.filter(
            is_delete=True,  # Product is not deleted
            variants__is_delete=True,  # At least one associated variant is not deleted
            product_images__is_delete=True,  # At least one associated image is not deleted
            category__is_active=True
        ).distinct().prefetch_related('product_images', 'variants')  # Prefetch for efficient queries
        

        for product in products:
            variants = list(product.variants.all())
            for variant in variants:
                if variant.is_offer and variant.offer_discount is not None:
                    variant.discounted_price = max(variant.price - variant.offer_discount, 0)
                else:
                    variant.discounted_price = variant.price
            product.variants_list = variants

        context['products'] = products
        return context


class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        errors = {}

        user = Users.objects.filter(email=email)
        if user:

            if not email:
                errors['email'] = "Email cannot be blank."

            if not password:
                errors['password'] = "Password cannot be blank."

            if not errors:
                user = authenticate(request, email=email, password=password)
                if user is not None:
                    if user.is_active is True:
                        login(request, user)
                        messages.success(request, "Happy to see u again")
                        return redirect('home') 
                    else:
                        errors['general'] = "Your account is inactive. Please contact support."
                        return redirect('inactive_account_page')
                else:
                    errors['general'] = "Invalid email or password."
        else:
            errors['general'] = "This email does not exist"

        return render(request, self.template_name, {'errors': errors})

class ProductDetailView(View):
    template_name = 'product_detail.html'

    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        variants = ProductVariant.objects.filter(product=product, is_delete=True)
        images = ProductImage.objects.filter(product=product,is_delete=True)
        user_wishlist = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True) if request.user.is_authenticated else []

        for variant in variants:
            if variant.offer_discount:
                variant.original_price = variant.price
                variant.discounted_price = variant.price - variant.offer_discount
                # Calculate discount percentage for display
                variant.discount_percentage = (variant.offer_discount / variant.price) * 100
            else:
                variant.original_price = variant.price
                variant.discounted_price = variant.price
                variant.discount_percentage = 0

        related_products = (
            Product.objects.filter(
                Q(category=product.category) & ~Q(id=product.id) & ~Q(is_delete=False)
            )
            .annotate(min_price=Min('variants__price'))  
            .prefetch_related('variants','product_images')  
            .distinct()[:4] 
        )
        
        distinct_colors = variants.values_list('color', flat=True).distinct()
        distinct_sizes = variants.values_list('size', flat=True).distinct()
            
        context = {
            'product': product,
            'variants': variants,
            'images': images,
            'related_products': related_products,
            'distinct_colors': distinct_colors,
            'distinct_sizes': distinct_sizes,
            'user_wishlist': user_wishlist,
        }
        return render(request, self.template_name, context)
class CustomLogoutView(View):
   def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('home') 

# class ProductListing(View):
#     def get(self,request):
#         return render(request,'product_listing.html')
class AccountInactive(TemplateView):
    template_name='inactive.html'   

class QuantityView(View):
    def get(self, request, *args, **kwargs):
        # Extract 'product_id', 'color', and 'size' from query parameters
        product_id = request.GET.get('product_id')
        color = request.GET.get('color')
        size = request.GET.get('size')

        if not product_id or not color or not size:
            return JsonResponse({'error': 'Product ID, color, and size are required'}, status=400)

        # Query the database for the product variant
        try:
            # Calculate discount information
            variant = get_object_or_404(ProductVariant, product_id=product_id, color=color, size=size)
            print(variant)

            has_discount = variant.is_offer
            discounted_price = variant.price - variant.offer_discount if has_discount else variant.price
            discount_percentage = (variant.offer_discount / variant.price) * 100 if has_discount else 0
            response_data = {
                'quantity': variant.available_quantity,
                'original_price': variant.price,
                'has_discount': has_discount,
                'discount_amount': variant.offer_discount if has_discount else 0,
                'discounted_price': discounted_price,
                'discount_percentage': round(discount_percentage, 2)
            }
            
            return JsonResponse(response_data)
        except ProductVariant.DoesNotExist:
            return JsonResponse({'quantity': 0, 'price': None})
        
@csrf_exempt
@require_POST
def toggle_wishlist(request):
    try:
        product_id = request.POST.get('product_id')
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Please log in to manage your wishlist.'}, status=401)
        if not product_id:
            return JsonResponse({'status': 'error', 'message': 'Product ID is required'}, status=400)
        
        # Fetch the product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Product does not exist'}, status=404)
        
        # Get or create wishlist entry
        wishlist_entry, created = Wishlist.objects.get_or_create(user=request.user, product=product)

        if created:
            # Product added to wishlist
            messages.success(request,"Product added to your wishlist")
            return JsonResponse({'status': 'success', 'message': 'Product added to your wishlist'})
        else:
            # Product removed from wishlist
            wishlist_entry.delete()
            return JsonResponse({'status': 'success', 'message': 'Product removed from your wishlist'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Something went wrong'}, status=500)

class PasswordResetView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data.get('email')
        
        try:
            user = Users.objects.get(email=email)
            self.generate_and_send_otp(email, request)
            
            # Store email for verification

            request.session['reset_email'] = email
            
            return JsonResponse({
                'success': True,
                'message': 'OTP has been sent to your email.',
                'redirect_url': reverse('verifyotpforget')
            })
            
        except Users.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'No account found with this email address.'
            })

    def generate_and_send_otp(self, email, request):
        otp = randint(100000, 999999)
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        send_mail(
            'Password Reset OTP',
            f'Your OTP for password reset is: {otp}. It is valid for 5 minutes.',
            'your_email@example.com',  # Update with your email
            [email],
            fail_silently=False,
        )
        messages.info(request, f'OTP sent to {email}. Please verify.')

class VerifyOTPViewForget(View):
    def get(self, request):
        return render(request, 'verify_otp_forget.html')

    def post(self, request):
        # Check which button was clicked
        if 'verify_otp' in request.POST:
            return self.verify_otp_func(request)
        elif 'resend_otp' in request.POST:
            self.generate_and_send_otp(request)
            messages.success(request, "A new OTP has been sent to your email.")
            return redirect('verifyotpforget')

    def verify_otp_func(self, request):
        otp_entered = request.POST.get('otp')
        stored_otp = request.session.get('otp')
        otp_generated_at_str = request.session.get('otp_generated_at')

        # Check if OTP is available and retrieve generation time
        if stored_otp and otp_generated_at_str:
            otp_generated_at = timezone.datetime.fromisoformat(otp_generated_at_str)
            expiration_time = otp_generated_at + timedelta(minutes=5)

            # Validate OTP within 5 minutes
            if timezone.now() <= expiration_time:
                if str(stored_otp) == otp_entered:
                    
                    # Clear OTP from session
                    request.session.pop('otp', None)
                    request.session.pop('otp_generated_at', None)

                    messages.success(request, "OTP verified successfully!.")
                    return redirect('set_new_password')
                else:
                    messages.error(request, "Invalid OTP. Please try again.")
            else:
                messages.error(request, "OTP has expired. Please request a new OTP.")
                return redirect('verifyotpforget')

        return render(request, 'verify_otp_forget.html')

    def generate_and_send_otp(self, request):
        otp = randint(100000, 999999)
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        email = request.session['reset_email']
        send_mail(
            'Resend  OTP Code',
            f'Your OTP is {otp}. It is valid for 5 minutes.',
            'your_email@example.com',
            [email],
            fail_silently=False,
        )
        
class SetNewPasswordView(View):
    def get(self, request):
        if not request.session.get('reset_email'):
            messages.error(request, 'Please complete email verification first')
            return redirect('login')
        return render(request, 'set_forget_password.html')

    def post(self, request):
        email = request.session.get('reset_email')
        if not email:
            messages.error(request, 'Session expired. Please try again')
            return redirect('login')

        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'set_forget_password.html')

        try:
            user = Users.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # Clear all session data
            del request.session['reset_email']
            messages.success(request, 'Password has been reset successfully. Please login with your new password.')
            return redirect('login')

        except Users.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('login')
        


    
class ProductGridList(View):
    def get_all_products(self, category_names=None, color=None, size=None, min_price=None, max_price=None, search=None, sort=None):
        filters = {
            'is_delete': True,
            'category__is_active': True
        }
        
        # If category_names is provided, fetch the corresponding category IDs
        if category_names:
            categories = Category.objects.filter(name__in=category_names)
            filters['category__in'] = categories  # Use the category IDs for filtering
        
        if color:
            filters['variants__color'] = color
        if size:
            filters['variants__size__in'] = size  # Use __in to filter by multiple sizes
        if min_price is not None:
            filters['variants__price__gte'] = min_price
        if max_price is not None:
            filters['variants__price__lte'] = max_price
        if search:
            filters['title__icontains'] = search  # Assuming the product name field is 'name'

        products = (
            Product.objects.filter(**filters)
            .annotate(variant_count=Count('variants', filter=Q(variants__is_delete=True, variants__stock_status=True)))  # Count valid variants
            .filter(variant_count__gt=0)  # Exclude products with no valid variants
            .distinct()
        )

        if sort == 'price-asc': 
            products = products.order_by('variants__price')
        elif sort == 'price-desc':
            products = products.order_by('-variants__price')
        elif sort == 'name-asc':
            products = products.order_by('title')  # Sort by product name A to Z
        elif sort == 'name-desc':
            products = products.order_by('-title')  # Sort by product name Z to A
    # 'featured' can be handled based on your specific logic for featured products

        product_data = []
        for product in products:
            variants = product.variants.filter(is_delete=True, stock_status=True)
            distinct_colors = set(variant.color for variant in variants)
            distinct_sizes = set(variant.size for variant in variants)

            product_variants = []
            for variant in variants:
                discounted_price = variant.price - variant.offer_discount if variant.is_offer else variant.price
                product_variants.append({
                    'price': variant.price,
                    'discounted_price': discounted_price,
                    'offer_discount': variant.offer_discount,
                    'is_offer': variant.is_offer,
                })

            product_data.append({
                'product': product,
                'colors': distinct_colors,
                'sizes': distinct_sizes,
                'variants': product_variants,
            })

        return product_data

   

    def get(self, request):
        # Handle AJAX request or normal page load
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # AJAX request to load filtered products
            category = request.GET.get('category')
            color = request.GET.get('color')
            size = request.GET.get('size')
            min_price = request.GET.get('min_price', 0)
            max_price = request.GET.get('max_price', 1000)
            search = request.GET.get('search')
            sort = request.GET.get('sort')

            # Parse category names
            category_names = category.split(',') if category else []

            # Get filtered product data
            product_data = self.get_all_products(category_names, color, size, min_price, max_price, search, sort)

            
            if request.user.is_authenticated:
                Wishlistdata = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
            else:
                Wishlistdata= None

            

            # Render partial HTML for the product grid
            rendered_html = render_to_string('partail_product_grid.html', {
                'product_data': product_data,
                'Wishlistdata': Wishlistdata,
            })

            return JsonResponse({'html': rendered_html})
        
        category = request.GET.get('category')  # Check if a category is passed in the query params
        active_categories = Category.objects.filter(is_active=True)
        
        return render(request, 'product_listing.html', {
            'active_categories': active_categories,
            'initial_category': category,  # Pass the category for client-side handling
            
        })
