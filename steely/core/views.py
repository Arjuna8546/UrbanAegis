from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.views import View
from core.models import Users,Product, ProductVariant, ProductImage,Category
from random import randint
from django.contrib.auth import authenticate, login,logout
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Min
from core.forms import RegisterForm
from django.http import JsonResponse
from django.core.paginator import Paginator


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
            messages.success(request, "A new OTP has been sent to your email.")
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
            'Your OTP Code',
            f'Your OTP is {otp}. It is valid for 5 minutes.',
            'your_email@example.com',
            [email],
            fail_silently=False,
        )
        messages.info(request, "A new OTP has been sent to your email.")


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context['user'] = self.request.user

        products = Product.objects.filter(
            is_delete=True,  # Product is not deleted
            variants__is_delete=True,  # At least one associated variant is not deleted
            product_images__is_delete=True  # At least one associated image is not deleted
        ).distinct().prefetch_related('product_images', 'variants')  # Prefetch for efficient queries


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
        }
        return render(request, self.template_name, context)
class CustomLogoutView(View):
   def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('home') 

class ProductListing(View):
    def get(self,request):
        return render(request,'product_listing.html')
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
            variant = get_object_or_404(ProductVariant, product_id=product_id, color=color, size=size)
            return JsonResponse({'quantity': variant.available_quantity, 'price': variant.price})
        except ProductVariant.DoesNotExist:
            return JsonResponse({'quantity': 0, 'price': None})  # Return 0 and None if not found
        
class ProductShow(View):
    def get(self, request):
        # Filter active products and prefetch related variants and images
        products = Product.objects.filter(is_delete=True).prefetch_related(
            'variants', 'product_images'
        )
        product_data = []

        for product in products:
            product_variants = product.variants.filter(is_delete=True)
            product_images = product.product_images.filter(is_delete=True)
            # Build product data
            product_data.append({
                "id": product.id,
                "name": product.title,
                "description": product.description,
                "category": product.category.name,
                "variants": [
                    {
                        "id": variant.id,
                        "price": f"${variant.price:.2f}",
                        "color": variant.color,
                        "size": variant.size,
                        "stock_status": variant.stock_status,
                        "available_quantity": variant.available_quantity,
                        "sku": variant.sku,
                    } for variant in product_variants
                ],
                "images": [image.image_url for image in product_images],
            })

        return JsonResponse(product_data, safe=False)
    
class ProductListView(View):
     def get(self, request):
        # Fetch all active categories
        active_categories = Category.objects.filter(is_active=True)

        # Fetch all active products
        products = Product.objects.filter(is_delete=False).prefetch_related('variants', 'product_images').order_by('-id')
        # Pagination logic
        paginator = Paginator(products, 12)  # 16 products per page (3 rows × 4 products)
        page_number = request.GET.get('page')  # Get the current page number from the query params
        page_obj = paginator.get_page(page_number)  # Get the products for the current page

        # Pass data to the template
        return render(request, "prduct_show.html", {
            "active_categories": active_categories,
            "page_obj": page_obj,  # Paginated products
        })

class FilteredProductList(View):
    def get(self, request):
        # Extract query parameters
        categories = request.GET.get('categories', '').split(',') if request.GET.get('categories') else []
        colors = request.GET.get('colors', '').split(',') if request.GET.get('colors') else []
        sizes = request.GET.get('sizes', '').split(',') if request.GET.get('sizes') else []
        max_price = request.GET.get('price', None)
        search_query = request.GET.get('search', '').strip()
        # Base queryset
        products = Product.objects.filter(is_delete=True)
        

        # Filter by categories
        if categories:
            products = products.filter(category__name__in=categories)


        # Filter by product variants
        if colors or sizes or max_price:
            variant_filter = {}

            if colors:
                variant_filter['color__in'] = colors
            if sizes:
                variant_filter['size__in'] = sizes
            if max_price:
                try:
                    variant_filter['price__lte'] = float(max_price)  # Ensure numeric comparison
                except ValueError:
                    return JsonResponse({'error': 'Invalid price value'}, status=400)

            product_ids = ProductVariant.objects.filter(
                is_delete=True,
                stock_status=True,
                **variant_filter
            ).values_list('product_id', flat=True).distinct()

            products = products.filter(id__in=product_ids)

        if search_query:
                products = products.filter(
                    Q(title__icontains=search_query) |
                    Q(variants__sku__icontains=search_query)
                ).distinct()
             

        # Prepare the response
        data = []
        for product in products.distinct():
            variants = product.variants.filter(is_delete=True, stock_status=True)
            images = product.product_images.filter(is_delete=True).values_list('image_url', flat=True)

            data.append({
                'id': product.id,
                'name': product.title,
                'description': product.description,
                'category': product.category.name,
                'variants': [
                    {
                        'price': variant.price,
                        'color': variant.color,
                        'size': variant.size,
                    } for variant in variants
                ],
                'images': list(images)
            })

        return JsonResponse(data, safe=False)
    

