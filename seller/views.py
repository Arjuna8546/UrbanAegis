import datetime
from decimal import Decimal
from django.db.models import Prefetch
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.contrib.auth import authenticate, login,logout
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.generic import ListView,UpdateView,TemplateView
from core.models import Users,Category
from core.models import Product, ProductVariant, Category,ProductImage,Order,OrderItem
from django.urls import reverse_lazy
from django.urls import reverse
from django.conf import settings
from cloudinary.uploader import upload
from cloudinary.exceptions import Error
from django.db import transaction
import logging
from django.db.models import Q
from seller.forms import AdminLoginForm
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
import json
from datetime import datetime, timedelta
from django.db.models import Sum
from django.utils.timezone import now
from django.template.loader import render_to_string
from weasyprint import HTML

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
                messages.info(request, f"Welcome back ADMIN.")
                return redirect('admin_dashboard') 
            else:
                form.add_error(None, "Invalid email or password.")
            
        return render(request, self.template_name, {'form': form})

class AdminLogOutView(View):  
    def get(self, request):
        logout(request)
        messages.error(request, f"see you soon ADMIN.")
        return redirect('admin_login')

                      
class AdminDashboardView(View):
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def get(self, request):
        # Calculate total sales
        total_sales = Order.objects.aggregate(total_sales=Sum('total_amount'))['total_sales'] or 0

        # Calculate total orders
        total_orders = Order.objects.count()

        # Best selling product
        best_selling_product = (
            OrderItem.objects.values('product_variant__product__title')
            .annotate(quantity_sold=Sum('quantity'))
            .order_by('-quantity_sold')
            .first()
        )

        # Best selling category
        best_selling_category = (
            OrderItem.objects.values('product_variant__product__category__name')
            .annotate(quantity_sold=Sum('quantity'))
            .order_by('-quantity_sold')
            .first()
        )

        # Recent 8 orders
        recent_orders = Order.objects.select_related('user').order_by('-created_at')[:8]

        # Context data for the template
        context = {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'best_selling_product': best_selling_product['product_variant__product__title'] if best_selling_product else "No data",
            'best_selling_category': best_selling_category['product_variant__product__category__name'] if best_selling_category else "No data",
            'recent_orders': recent_orders,
        }

        return render(request, 'admin_dashboard.html', context)
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
    paginate_by = 10

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = ProductVariant.objects.select_related('product', 'product__category').order_by('-id')

        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(product__title__icontains=search_query) |  # Search by product title
                Q(product__category__name__icontains=search_query) |  # Search by category name
                Q(color__icontains=search_query)  # Search by variant color
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']
        
        # Add pagination context
        context['has_previous'] = page_obj.has_previous()
        context['has_next'] = page_obj.has_next()
        context['previous_page_number'] = page_obj.previous_page_number() if page_obj.has_previous() else None
        context['next_page_number'] = page_obj.next_page_number() if page_obj.has_next() else None
        context['page_range'] = list(page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

        context['search_query'] = self.request.GET.get('q', '')
        
        return context

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

                    variant_exists = ProductVariant.objects.filter(
                        product=product,
                        color=color,
                        size=size
                    ).exists()

                    if variant_exists:
                        messages.warning(request, f"Variant with SKU: {sku}, Color: {color}, Size: {size} already exists.")
                        continue  # Skip to the next variant if it already exists

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
        category_name = request.POST.get('categoryName').strip()
        category_status = request.POST.get('categoryStatus') == 'on'  # Checkbox will send 'on' if checked

        existing_category = Category.objects.filter(name__iexact=category_name).first()

        if existing_category:
            messages.error(request, f"Category '{category_name}' already exists.")
            return redirect('categorie') 
  
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
        variant_id = self.kwargs.get('pk')
        product_variant = get_object_or_404(ProductVariant, pk=variant_id)
        product = product_variant.product
        product_images = ProductImage.objects.filter(product=product)

        active_categories = Category.objects.filter(is_active=True)
        context['active_categories'] = active_categories
        context['product_variant'] = product_variant
        context['product'] = product
        context['product_images'] = product_images
        
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
        active_status = request.POST.get('active-status')
        if active_status == 'active':
            product_variant.is_delete = True
        elif active_status == 'in-active':
            product_variant.is_delete = False
        
        
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
            # product.product_images.all().delete()  

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
    
def delete_product_image(request, image_id):
    if request.method == 'DELETE':
        image = get_object_or_404(ProductImage, id=image_id)
        image.delete()  # Or update is_delete field if you use soft delete
        return JsonResponse({'message': 'Image deleted successfully'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

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
            # Success message for product deletion
            messages.success(
                request, f"Product '{product.title}' and all associated variants and images have been deleted successfully."
            )

        elif entity_type == "variant":
            # Soft delete the selected variant
            variant.is_delete = False
            variant.save()

            # Success message for variant deletion
            messages.success(request, f"Variant  has been deleted successfully.")

        # Redirect to the product list page
        return redirect(reverse_lazy('product'))
class OrderDetails(View):
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def get(self, request):
        page = request.GET.get('page', 1)
        items_per_page = 10
        search_query = request.GET.get('search', '').strip()
        # Optimize query with select_related and prefetch_related
        orders = Order.objects.prefetch_related(
            Prefetch(
                'order_items',
                queryset=OrderItem.objects.select_related('product_variant__product'),
            )
        ).select_related('user').order_by('-created_at')  # Order by newest first

        if search_query:
            orders = orders.filter(
                Q(status_of_order__icontains=search_query) |  # Search by status_of_order (case-insensitive)
                Q(order_id__icontains=search_query)  # Search by order ID
            )


        # Implement pagination
        paginator = Paginator(orders, items_per_page)
        try:
            current_page = paginator.page(page)
        except PageNotAnInteger:
            current_page = paginator.page(1)
        except EmptyPage:
            current_page = paginator.page(paginator.num_pages)

        # Get the page range for template
        page_range = list(paginator.get_elided_page_range(current_page.number, on_each_side=2, on_ends=1))

        context = {
            "orders": current_page,
            "page_obj": current_page,
            "is_paginated": True,
            "page_range": page_range,
            "has_previous": current_page.has_previous(),
            "has_next": current_page.has_next(),
            "previous_page_number": current_page.previous_page_number() if current_page.has_previous() else None,
            "next_page_number": current_page.next_page_number() if current_page.has_next() else None,
            "search_query": search_query, 
        }

        return render(request, "orders_detail.html", context)
    
    
class SpecificOrderDetail(View):

    template_name = 'sepcific_order_detail.html'

    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def get(self, request, order_id):
        # Fetch the order
        order = get_object_or_404(Order, id=order_id)

        # Fetch order items
        order_items = OrderItem.objects.filter(order=order).select_related(
            'product_variant__product'
        )

        # Fetch user and address details
        user = order.user
        status_of_order= order.status_of_order
        address = order.address_id
        shipping_fee = "FREE" if order.total_amount > 500 else "50"
        total_tax = sum(item.tax for item in order.order_items.all())
        sub_total = order.subtotal
        discount = order.discount

        # Fetch product and variant details
        product_variants = [
            item.product_variant for item in order_items
        ]
        products = [
            variant.product for variant in product_variants
        ]

        context = {
            'order': order,
            'order_items': order_items,
            'products': products,
            'product_variants': product_variants,
            'user': user,
            'address': address,
            'status_of_order':status_of_order,
            'shipping_fee':shipping_fee,
            'sub_total': sub_total,
            'discount': discount,
        }
        return render(request, self.template_name, context)

class UpdateOrderStatusView(View):
    def post(self, request, order_id):
        # Retrieve the order object
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status_of_order')

        # Allow 'Cancelled' status regardless of payment status
        if new_status == "Cancelled" or new_status == "Pending":
            order.status_of_order = new_status
            order.save()
            messages.success(request, "Order status updated to 'Cancelled' successfully!")
        # Check other statuses only if payment is 'Paid'
        elif order.payment_status == "paid" and new_status in ["Processing", "Shipped", "Delivered"]:
            order.status_of_order = new_status
            order.save()
            messages.success(request, "Order status updated successfully!")
        else:
            if new_status != "Cancelled":
                messages.error(request, "Cannot update status. Payment has not been completed.")
            else:
                messages.error(request, "Invalid status update.")

        # Redirect to the previous page or a default URL
        return redirect(request.META.get('HTTP_REFERER', '/'))


class SalesReport(View):
    @method_decorator(user_passes_test(lambda user: user.is_authenticated and user.is_superuser, login_url='admin_login'))
    def get(self,request):
        filter_type = request.GET.get('filter_type', 'all')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        page = request.GET.get('page', 1)
        items_per_page = 10

        orders = Order.objects.all().prefetch_related('order_items').order_by('-created_at')


        if filter_type == 'daily':
            today = now().date()
            orders = orders.filter(created_at__date=today)
        elif filter_type == 'weekly':
            start_of_week = now().date() - timedelta(days=now().weekday())
            end_of_week = start_of_week + timedelta(days=6)
            orders = orders.filter(created_at__date__range=[start_of_week, end_of_week])
        elif filter_type == 'monthly':
            first_of_month = now().replace(day=1)
            orders = orders.filter(created_at__date__gte=first_of_month)
        elif filter_type == 'yearly':
            first_of_year = now().replace(month=1, day=1)
            orders = orders.filter(created_at__date__gte=first_of_year)
        elif filter_type == 'custom' and start_date and end_date:
            # Parse the custom date range
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                orders = orders.filter(created_at__date__range=[start_date, end_date])
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
        # Calculate totals from all orders before pagination
        total_order = orders.count()
        total_sales = orders.aggregate(Sum('subtotal'))['subtotal__sum'] or Decimal('0.00')
        total_discount = orders.aggregate(Sum('discount'))['discount__sum'] or Decimal('0.00')
        net_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        # Implement pagination
        paginator = Paginator(orders, items_per_page)
        try:
            current_page = paginator.page(page)
        except PageNotAnInteger:
            current_page = paginator.page(1)
        except EmptyPage:
            current_page = paginator.page(paginator.num_pages)

        # Get the page range for template
        page_range = list(paginator.get_elided_page_range(current_page.number, on_each_side=2, on_ends=1))

        context = {
            "orders": current_page,
            "total_order": total_order,
            "total_sales": total_sales,
            "total_discount": total_discount,
            "net_revenue": net_revenue,
            "filter_type": filter_type,
            "start_date": start_date,
            "end_date": end_date,
            # Pagination context
            "page_obj": current_page,
            "is_paginated": True,
            "page_range": page_range,
            "has_previous": current_page.has_previous(),
            "has_next": current_page.has_next(),
            "previous_page_number": current_page.previous_page_number() if current_page.has_previous() else None,
            "next_page_number": current_page.next_page_number() if current_page.has_next() else None,
        }

        return render(request, 'admin_sales_report.html', context)
    
class GenerateSalesReportPDF(View):
    def get(self, request):
        filter_type = request.GET.get("filter_type", "all")
        start_date_str = request.GET.get("start_date", "")
        end_date_str = request.GET.get("end_date", "")

        

        orders = Order.objects.all().prefetch_related('order_items')

        if filter_type == 'daily':
            today = now().date()
            orders = orders.filter(created_at__date=today)
        elif filter_type == 'weekly':
            start_of_week = now().date() - timedelta(days=now().weekday())
            end_of_week = start_of_week + timedelta(days=6)
            orders = orders.filter(created_at__date__range=[start_of_week, end_of_week])
        elif filter_type == 'monthly':
            first_of_month = now().replace(day=1)
            orders = orders.filter(created_at__date__gte=first_of_month)
        elif filter_type == 'yearly':
            first_of_year = now().replace(month=1, day=1)
            orders = orders.filter(created_at__date__gte=first_of_year)
        elif filter_type == 'custom' and start_date_str and end_date_str:
            # Parse the custom date range
            try:
                start_date = datetime.strptime(start_date_str, "%b. %d, %Y")
                end_date = datetime.strptime(end_date_str, "%b. %d, %Y")

                # Format to YYYY-MM-DD for database filtering
                start_date_formatted = start_date.strftime("%Y-%m-%d")
                end_date_formatted = end_date.strftime("%Y-%m-%d")
                orders = orders.filter(created_at__date__range=[start_date_formatted, end_date_formatted])
            except ValueError:
                messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")


        # Prepare context for the template
        context = {
            "orders": orders,
            "filter_type": filter_type,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "total_orders": orders.count(),
            "total_sales": sum(order.subtotal for order in orders),
            "total_discount": sum(order.discount for order in orders),
            "net_revenue": sum(order.total_amount for order in orders),
        }

        # Render HTML template
        html_string = render_to_string("sales_reprt_template.html", context)

        # Generate PDF
        pdf = HTML(string=html_string).write_pdf()

        # Create HTTP response
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="sales_report_{filter_type}.pdf"'
        return response
    
class ContactView(TemplateView):
    template_name= "contact.html"