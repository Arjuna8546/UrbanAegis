from django.db.models import Q, Exists, OuterRef
from django.views import View
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.views.generic import ListView
from django.views.generic import UpdateView
from core.models import Users,Category
from core.models import Product, ProductVariant, Category,ProductImage
from django.urls import reverse_lazy
from django.urls import reverse
from django.conf import settings
from cloudinary.uploader import upload
from cloudinary.exceptions import Error
from django.db import transaction
import logging
from seller.forms import AdminLoginForm
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
import json

class AdminLoginView(View):
    template_name = 'admin_login.html'  
    def get(self, request):
        form = AdminLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            
            if user is not None and user.is_superuser is True:
                login(request, user)
                return redirect('admin_dashboard') 
            else:
                form.add_error(None, "Invalid email or password.")
            
        return render(request, self.template_name, {'form': form})

class AdminLogOutView(View):  
    def get(self, request):
        logout(request)
        return redirect('admin_login')

                      
class AdminDashboardView(View):
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def get(self, request):
        return render(request, 'admin_dashboard.html')
class AdminCoustomersView(ListView):
    model = Users
    template_name = 'coustomers.html'
    context_object_name = 'users'

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        # Retrieve only specific fields to optimize the query
        return Users.objects.filter(is_superuser=False).values('id', 'first_name', 'last_name', 'email', 'join_date','is_active')
    
class ToggleActiveStatusView(View):
    def post(self, request, user_id):
        user = get_object_or_404(Users, id=user_id)
        user.is_active = not user.is_active  # Toggle the active status
        user.save()
        if user.is_active:
            messages.success(request, f"User '{user.first_name} {user.last_name}' has been activated successfully.")
        else:
            messages.error(request, f"User '{user.first_name} {user.last_name}' has been deactivated successfully.")

        return redirect('coustomers')


class ProductListView(ListView):
    template_name = 'product.html'
    context_object_name = 'variants'

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return ProductVariant.objects.filter(
            is_delete=True,
            product__is_delete=True
        ).select_related('product', 'product__category')

logger = logging.getLogger(__name__)

class ProductCreateView(View):
    template_name = 'add_product.html'

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {'categories': categories})

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                # Get product details
                title = request.POST.get('title')
                description = request.POST.get('description')
                category_id = request.POST.get('category')

                # Check if the product exists; create it if not
                product = Product.objects.filter(title=title).first()
                if not product:
                    product = Product.objects.create(
                        title=title,
                        description=description,
                        category_id=category_id
                    )
                else:
                    messages.info(request, "Product already exists. Adding variants.")
                
                sku = request.POST.get('sku')
                price = request.POST.get('price')
                is_in_stock = request.POST.get('stock') == 'in-stock'
                quantity = request.POST.get('quantity')
                color = request.POST.get('color')
                size = request.POST.get('size')

                ProductVariant.objects.create(
                        product=product,
                        sku=sku,
                        stock_status=is_in_stock,
                        color=color,
                        size=size,
                        price=price,
                        available_quantity=quantity
                    )

                # Handle uploaded images (linked to the product)
                images = request.FILES.getlist('productImages')  # Name the file input `productImages` in the form
                print(images)
                image_urls = []

                for image in images:
                    try:
                        # Upload the image to Cloudinary
                        upload_result = upload(image, folder='urbanaegis1')
                        image_url = upload_result['secure_url']
                        image_urls.append(image_url)

                        # Save the image to the database
                        ProductImage.objects.create(
                            product=product,  # Associate the image with the product
                            image_url=image_url
                        )
                        logger.info(f"Image uploaded successfully: {image_url}")
                    except Exception as e:
                        logger.error(f"Failed to upload image {image.name}: {str(e)}")
                        messages.warning(request, f"Failed to upload image {image.name}: {str(e)}")

                if not image_urls:
                    logger.warning("No images were uploaded for the product.")
                    messages.warning(request, "No images were uploaded for the product.")
                else:
                    logger.info(f"Total images uploaded for the product: {len(image_urls)}")
                
                

                # Parse and save variants
                variants_json = request.POST.get('variants')
                print(variants_json)
                variants = json.loads(variants_json) if variants_json else []

                for variant_data in variants:
                    sku = variant_data.get('sku')
                    price = variant_data.get('price')
                    is_in_stock = True
                    quantity = variant_data.get('quantity')
                    color = variant_data.get('color')
                    size = variant_data.get('size')

                    # Create the product variant
                    ProductVariant.objects.create(
                        product=product,
                        sku=sku,
                        stock_status=is_in_stock,
                        color=color,
                        size=size,
                        price=price,
                        available_quantity=quantity
                    )

                messages.success(request, "Product, images, and variants added successfully!")
                return redirect('product')  

            except Exception as e:
                transaction.set_rollback(True)
                logger.error(f"An error occurred while creating the product: {str(e)}")
                messages.error(request, f"An error occurred: {str(e)}")
                return redirect('add_product')  
  




class CategoryView(View):
    
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        return render(request, 'categorie.html', {'categories': categories})

    def post(self, request, *args, **kwargs):
        category_name = request.POST.get('categoryName')
        category_status = request.POST.get('categoryStatus') == 'on'  # Checkbox will send 'on' if checked

  
        new_category = Category.objects.create(
            name=category_name,
            is_active=category_status
        )

        messages.success(request, f"Category '{new_category.name}' has been added successfully.")


        return redirect('categorie')


    
class ToggleCategoryStatusView(View):
    def post(self, request, category_id):
        category = Category.objects.get(id=category_id)
        category.is_active = not category.is_active
        category.save()
        if category.is_active:
            messages.success(request, f"'{category.name}' has been activated successfully.")
        else:
            messages.error(request, f"'{category.name}' has been deactivated successfully.")
        return redirect(reverse('categorie'))


class ProductVariantUpdateView(UpdateView):
    template_name = 'update_product_variant.html'
    model = ProductVariant
    fields = ['sku', 'stock_status', 'price', 'available_quantity', 'color', 'size']  

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        active_categories = Category.objects.filter(is_active=True)
        context['active_categories'] = active_categories
        
        return context

    def post(self, request, *args, **kwargs):
        product_variant = get_object_or_404(ProductVariant, id=kwargs['pk'])
        product = product_variant.product  
        
        if 'title' in request.POST and request.POST['title']:
            product.title = request.POST['title']
        if 'description' in request.POST and request.POST['description']:
            product.description = request.POST['description']
        if 'category' in request.POST and request.POST['category']:
            product.category_id = request.POST['category']
        
        product.save()


        if 'sku' in request.POST and request.POST['sku']:
            product_variant.sku = request.POST['sku']
        stock_status = request.POST.get('stock')
        if stock_status == 'in-stock':
            product_variant.stock_status = True
        elif stock_status == 'out-of-stock':
            product_variant.stock_status = False
        if 'price' in request.POST and request.POST['price']:
            product_variant.price = request.POST['price']
        if 'quantity' in request.POST and request.POST['quantity']:
            product_variant.available_quantity = request.POST['quantity']
        if 'color' in request.POST and request.POST['color']:
            product_variant.color = request.POST['color']
        if 'size' in request.POST and request.POST['size']:
            product_variant.size = request.POST['size']

        if 'productImage' in request.FILES:
            images = request.FILES.getlist('productImage')  # Multiple image files

            # Delete existing product images before adding new ones
            product.product_images.all().delete()  

            for image in images:
                try:
                    upload_result = upload(image)
                    image_url = upload_result['secure_url']
                    ProductImage.objects.create(
                        product=product,
                        image_url=image_url
                    )
                except Exception as e:
                    messages.warning(request, f"Failed to upload image {image.name}: {str(e)}")
        
        product_variant.save()

        messages.warning(request, "Product and variant updated successfully!")
        return redirect(reverse_lazy('product'))

class ChooseDeleteProductOrVariantView(View):
    
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product = variant.product  
        return render(request, 'choose_delete_product_or_variant.html', {
            'variant': variant,
            'product': product
        })

class ConfirmDeleteProductOrVariantView(View):
    def post(self, request, variant_id, entity_type):
        # Get the variant and its associated product
        variant = get_object_or_404(ProductVariant, id=variant_id, is_delete=True)
        product = variant.product

        if entity_type == "product":
            # Soft delete the product and all related entities
            ProductVariant.objects.filter(product=product).update(is_delete=False)
            ProductImage.objects.filter(product=product).update(is_delete=False)  # Adjusted to work with your model
            product.is_delete = False
            product.save()

            # Success message for product deletion
            messages.success(
                request, f"Product '{product.title}' and all associated variants and images have been deleted successfully."
            )

        elif entity_type == "variant":
            # Soft delete the selected variant
            variant.is_delete = False
            variant.save()

            # Success message for variant deletion
            messages.success(request, f"Variant '{variant.sku}' has been deleted successfully.")

        # Redirect to the product list page
        return redirect(reverse_lazy('product'))





