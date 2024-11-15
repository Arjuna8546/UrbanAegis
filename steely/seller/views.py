from django.db.models import Q, Exists, OuterRef
from django.views import View
from django.contrib.auth import authenticate, login
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
                      
class AdminDashboardView(View):
    def get(self, request):
        return render(request, 'admin_dashboard.html')
class AdminCoustomersView(ListView):
    model = Users
    template_name = 'coustomers.html'
    context_object_name = 'users'

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

    def get_queryset(self):
        # Exclude ProductVariant with is_delete=True and related Product with is_delete=True
        return ProductVariant.objects.filter(
            is_delete=True,
            product__is_delete=True
        ).select_related('product', 'product__category')

logger = logging.getLogger(__name__)

class ProductCreateView(View):
    template_name = 'add_product.html'

    def get(self, request, *args, **kwargs):
        categories = Category.objects.filter(is_active=True)
        return render(request, self.template_name, {'categories': categories})

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                # Extract product data from the form
                title = request.POST.get('title')
                description = request.POST.get('description')
                category_id = request.POST.get('category')

                product = Product.objects.filter(title=title).first()

                if not product:
                    # If product doesn't exist, create it
                    product = Product.objects.create(
                        title=title,
                        description=description,
                        category_id=category_id
                    )
                    
                else:
                    pass
                # Extract variant data from the form
                sku = request.POST.get('sku')
                price = request.POST.get('price')
                is_in_stock = request.POST.get('stock') == 'in-stock'
                quantity = request.POST.get('quantity')
                color = request.POST.get('color')
                size = request.POST.get('size')

                # Create the product variant
                variant = ProductVariant.objects.create(
                    product=product,
                    sku=sku,
                    stock_status=is_in_stock,
                    color=color,
                    size=size,
                    price=price,
                    available_quantity=quantity
                )

                # Handle multiple image uploads
                images = request.FILES.getlist('productImage')
                print(len(images))
                

                image_urls = []  # List to store uploaded image URLs

                # Iterate through each uploaded image and upload to Cloudinary
                for image in images[1:]:
                    try:
                        # Upload image to Cloudinary and get the URL
                        upload_result = upload(image, folder='urban_aegis')
                        image_url = upload_result['secure_url']
                        image_urls.append(image_url)

                        # Save each image URL to the ProductImage model
                        ProductImage.objects.create(
                            variant=variant,
                            image_url=image_url
                        )
                        logger.info(f"Image uploaded successfully: {image_url}")

                    except Exception as e:
                        logger.error(f"Failed to upload image {image.name}: {str(e)}")
                        messages.warning(request, f"Failed to upload image {image.name}: {str(e)}")

                # If no images were uploaded successfully
                if not image_urls:
                    logger.warning("No images were uploaded.")
                    messages.warning(request, "No images were uploaded.")
                else:
                    logger.info(f"Total images uploaded: {len(image_urls)}")

                messages.success(request, "Product and images added successfully!")
                return redirect('product')  # Redirect to product list page

            except Exception as e:
                # In case of any error, rollback the transaction and show error message
                transaction.set_rollback(True)
                logger.error(f"An error occurred while creating product: {str(e)}")
                messages.error(request, f"An error occurred: {str(e)}")
                return redirect('add_product')  # Redirect back to the add product page




class CategoryView(View):
    def get(self, request, *args, **kwargs):
        # Handle GET request to display the form and list existing categories
        categories = Category.objects.all()
        return render(request, 'categorie.html', {'categories': categories})

    def post(self, request, *args, **kwargs):
        # Handle POST request to add a new category
        category_name = request.POST.get('categoryName')
        category_status = request.POST.get('categoryStatus') == 'on'  # Checkbox will send 'on' if checked

        # Save the category to the database
        new_category = Category.objects.create(
            name=category_name,
            is_active=category_status
        )

        messages.success(request, f"Category '{new_category.name}' has been added successfully.")

        # Redirect to the same page after the category is added
        return redirect('categorie')


    
class ToggleCategoryStatusView(View):
    def post(self, request, category_id):
        # Toggle the category's status
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
    fields = ['sku', 'stock_status', 'price', 'available_quantity', 'color', 'size']  # Exclude image field, we'll handle it separately

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active categories for the select field
        active_categories = Category.objects.filter(is_active=True)
        context['active_categories'] = active_categories
        
        return context

    def post(self, request, *args, **kwargs):
        product_variant = get_object_or_404(ProductVariant, id=kwargs['pk'])
        product = product_variant.product  # Access the related Product instance
        
        # Update fields for the Product model only if provided in the request data
        if 'title' in request.POST and request.POST['title']:
            product.title = request.POST['title']
        if 'description' in request.POST and request.POST['description']:
            product.description = request.POST['description']
        if 'category' in request.POST and request.POST['category']:
            product.category_id = request.POST['category']
        
        # Save changes to the Product model
        product.save()

        # Update fields for the ProductVariant model only if provided in the request data
        if 'sku' in request.POST and request.POST['sku']:
            product_variant.sku = request.POST['sku']
        if 'stock' in request.POST:
            product_variant.stock_status = True if request.POST['stock'] == 'in-stock' else False
        if 'price' in request.POST and request.POST['price']:
            product_variant.price = request.POST['price']
        if 'quantity' in request.POST and request.POST['quantity']:
            product_variant.available_quantity = request.POST['quantity']
        if 'color' in request.POST and request.POST['color']:
            product_variant.color = request.POST['color']
        if 'size' in request.POST and request.POST['size']:
            product_variant.size = request.POST['size']

        # Handle file upload for multiple product images
        if 'productImage' in request.FILES:
            images = request.FILES.getlist('productImage')  # Multiple image files

            # Delete existing product images before adding new ones
            product_variant.product_images.all().delete()  # Remove previous images

            for image in images:
                try:
                    # Upload image to Cloudinary
                    upload_result = upload(image)
                    image_url = upload_result['secure_url']

                    # Save each image URL to the database
                    ProductImage.objects.create(
                        variant=product_variant,
                        image_url=image_url
                    )
                except Exception as e:
                    messages.warning(request, f"Failed to upload image {image.name}: {str(e)}")
        
        # Save changes to the ProductVariant model
        product_variant.save()

        messages.warning(request, "Product and variant updated successfully!")
        return redirect(reverse_lazy('product'))

class ChooseDeleteProductOrVariantView(View):
    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product = variant.product  # Get the related product
        return render(request, 'choose_delete_product_or_variant.html', {
            'variant': variant,
            'product': product
        })

class ConfirmDeleteProductOrVariantView(View):
    def post(self, request, variant_id, entity_type):
        # Get the specific ProductVariant by its ID
        variant = get_object_or_404(ProductVariant, id=variant_id)
        product = variant.product  # Access the related Product instance

        if entity_type == "product":
            # Soft delete all variants and images associated with the product
            ProductVariant.objects.filter(product=product).update(is_delete=False)
            ProductImage.objects.filter(variant__product=product).update(is_delete=False)
            product.is_delete = False
            product.save()

            messages.error(request, f"Product '{product.title}' and all associated variants and images have been deleted successfully.")

        elif entity_type == "variant":
            # Soft delete only the specific variant and its images
            variant.is_delete = False
            variant.save()
            ProductImage.objects.filter(variant=variant).update(is_delete=False)
        
            messages.error(request, f"Variant '{variant.sku}' has been deleted successfully.")

        return redirect(reverse_lazy('product'))


