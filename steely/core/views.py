from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.views import View
from core.models import Users,Product, ProductVariant, ProductImage
from random import randint
from django.contrib.auth import authenticate, login,logout
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Min
from core.forms import RegisterForm


class RegisterView(View):
    def get(self, request):
        # Render the registration form
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Get the validated data from the form
            email = form.cleaned_data['email']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            password = form.cleaned_data['password']

            # Save user data temporarily in session
            request.session['user_data'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': password
            }

            # Generate and send OTP
            self.generate_and_send_otp(email, request)

            # Redirect to OTP verification page
            return redirect('verifyotp')

        # If the form is invalid, re-render with errors
        return render(request, 'register.html', {'form': form})

    def generate_and_send_otp(self, email, request):
        otp = randint(100000, 999999)  # Generate a random 6-digit OTP
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        # Send the OTP to the user's email
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
        # Render the OTP verification form
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
                    # OTP is valid; create and save the user
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
        # Generate a new OTP and update the session
        otp = randint(100000, 999999)
        request.session['otp'] = otp
        request.session['otp_generated_at'] = timezone.now().isoformat()

        # Send the new OTP to the user's email
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
        
        # Add the user to the context if they are authenticated
        if self.request.user.is_authenticated:
            context['user'] = self.request.user

        # Exclude products and variants with is_delete=True
        products = Product.objects.filter(
            is_delete=True,
            variants__is_delete=True,
            # variants__productimage__is_delete=True  # Check if images are also marked as deleted
        ).distinct()

        # Add the products to the context
        context['products'] = products
        return context


class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Initialize an empty dictionary for error messages
        errors = {}

        user = Users.objects.filter(email=email)
        if user:
        # Validate email
            if not email:
                errors['email'] = "Email cannot be blank."

            # Validate password
            if not password:
                errors['password'] = "Password cannot be blank."
            
            # If there are no field-level errors, attempt authentication
            if not errors:
                user = authenticate(request, email=email, password=password)
                if user is not None:
                    if user.is_active is True:
                        login(request, user)
                        return redirect('home')  # Redirect to a dashboard or homepage
                    else:
                        errors['general'] = "Your account is inactive. Please contact support."
                        return redirect('inactive_account_page')
                else:
                    errors['general'] = "Invalid email or password."
        else:
            errors['general'] = "This email does not exist"

        # Re-render the form with error messages if authentication fails
        return render(request, self.template_name, {'errors': errors})

class ProductDetailView(View):
    template_name = 'product_detail.html'

    def get(self, request, product_id):
        # Retrieve the specific product using its ID
        product = get_object_or_404(Product, id=product_id)

        # Retrieve all variants and images related to this product
        variants = ProductVariant.objects.filter(product=product, is_delete=True)
        print(len(variants))
        
        # Check if images are linked to ProductVariant or Product
        images = ProductImage.objects.filter(variant__product=product)

        # Fetch related products (from the same category, excluding the current product)
         # Fetch related products within the same category, excluding the current product
        related_products = (
            Product.objects.filter(
                Q(category=product.category) & ~Q(id=product.id)
            )
            .annotate(min_price=Min('variants__price'))  # Annotate with minimum price
            .prefetch_related('variants__product_images')  # Prefetch images for variants
            .distinct()[:4]  # Limit to 4 related products
        )
        
        
        context = {
            'product': product,
            'variants': variants,
            'images': images,
            'related_products': related_products,
        }
        return render(request, self.template_name, context)
class CustomLogoutView(View):
   def get(self, request, *args, **kwargs):
        # Log out the user
        logout(request)
        
        # Redirect to the desired page after logout
        return redirect('home')  # Replace 'home' with your desired redirect URL

class ProductListing(View):
    def get(self,request):
        return render(request,'product_listing.html')
class AccountInactive(TemplateView):
    template_name='inactive.html'   

