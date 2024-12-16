from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager
from django.db.models import Min
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_save
from django.dispatch import receiver
from utils.id_generator import generate_unique_id

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")

        return self.create_user(email, password, **extra_fields)


class Users(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    join_date = models.DateTimeField(default=timezone.now)
    phone_no = models.CharField(max_length=90, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # Required for admin access
    is_google = models.BooleanField(default=False)
    
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email

@receiver(post_save, sender=Users)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    if created:
        # Create a Wallet instance for the newly created user
        Wallet.objects.create(user=instance)    

class Category(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    description = models.TextField()
    is_delete = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=50)
    size = models.CharField(max_length=5, choices=[('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'Extra Large'), ('XXL', 'Double Extra Large')])
    available_quantity = models.PositiveIntegerField()
    stock_status = models.BooleanField(default=True)
    sku = models.CharField(max_length=100, unique=True,default="default")
    is_delete = models.BooleanField(default=True)
    is_offer = models.BooleanField(default=False)
    offer_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)



    def __str__(self):
        return f"{self.product.title} - {self.color} - {self.size}"

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='product_images', on_delete=models.CASCADE)
    image_url = models.URLField()
    is_delete = models.BooleanField(default=True)

    def __str__(self):
        return f"Image for {self.variant.sku}"
    
class UserAddress(models.Model):
    user = models.ForeignKey("Users",related_name="addresses", on_delete=models.CASCADE)
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def soft_delete(self):
        self.is_deleted = True
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.save()

class CartItem(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="cart", null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)  # For guest users
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    product_variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product} - x{self.quantity}"

    def get_price(self):
        if self.product_variant:
            base_price = self.product_variant.price
            if self.product_variant.is_offer and self.product_variant.offer_discount:
                return base_price - self.product_variant.offer_discount
            return base_price
        return self.product.price

    def get_total_price(self):
        """Calculate the total cost for this cart item."""
        return self.get_price() * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('razorpay', 'RazorPay'),
        ('cod', 'Cash on Delivery'),
    ]

    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="orders")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique order identifier
    order_id = models.CharField(max_length=12, unique=True, default=generate_unique_id)
    status_of_order = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    address_id = models.ForeignKey('UserAddress', on_delete=models.SET_NULL, null=True, related_name="orders_address") 

    customer_email = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20,blank=True, null=True)
    customer_name = models.CharField(max_length=255)

    # Shipping Address Details
    shipping_street = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_pincode = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100)
    
    # Reference to Address (can link to an Address model)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2,default=0.0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2,default=0.0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature_id = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(max_length=20, default='pending')  # Could use similar choices for status
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.uuid} - {self.user.first_name}"
    

class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name="order_items")  # Links to the specific order
    product_variant = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, related_name="order_items_product")
    quantity = models.PositiveIntegerField()  # Number of units of the product
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per unit of the product
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)  # Calculated total price for this item
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Tax applied to this item

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"OrderItem: {self.product_id} (Order {self.order.uuid})"

    def save(self, *args, **kwargs):
        # Automatically calculate the total price as (unit_price * quantity) + tax
        self.total_price = (self.unit_price * self.quantity) + self.tax
        super().save(*args, **kwargs)

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    code = models.CharField(max_length=20, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def is_active(self):
        now = timezone.now()
     

        return (
            
            now <= self.valid_until and now >= self.valid_from and
            (self.usage_limit is None or self.times_used < self.usage_limit)
        )

    def can_use(self, user, order_total):
        """
        Check if a user can use this coupon.
        """

        # Check if coupon is active
        if not self.status=='active':
            print(self.is_active)
            return False, "This coupon is not active."

        # Check minimum purchase amount
        if order_total < self.min_purchase:

            return False, f"Minimum purchase amount of {self.min_purchase} required."

        # Check if user has already used this coupon
        if CouponUsage.objects.filter(coupon=self, user=user).exists():
            return False, "You have already used this coupon."

        return True, "Coupon is valid."

    def calculate_discount(self, order_total):
        """
        Calculate the discount amount based on the coupon type and order total.
        """
        if self.discount_type == 'percentage':
            discount = order_total * (self.discount_value / 100)
        else:  # fixed amount
            discount = min(self.discount_value, order_total)  # Don't exceed order total
        return discount

    def use(self, user):
        """
        Mark the coupon as used by a user.
        """
        self.times_used += 1
        self.save()
        CouponUsage.objects.create(coupon=self, user=user)


class CouponUsage(models.Model):
    """
    Track which users have used which coupons to enforce one-time use per user.
    """
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['coupon', 'user']
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"

class Wishlist(models.Model):

    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)

    
class Offer(models.Model):

    DISCOUNT_TYPE_CHOICE=(
        ('percentage','Percentage'),
        ('fixed','Fixed amount'),
    )
    STATUS_CHOICE=(
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    discount_type = models.CharField(max_length=20,choices=DISCOUNT_TYPE_CHOICE)
    discount_value= models.DecimalField(max_digits=10,decimal_places=2)
    # valid_from = models.DateTimeField()
    # valid_until= models.DateTimeField()
    status = models.CharField(max_length=20,choices=STATUS_CHOICE,default='active')
    description = models.TextField()
    product = models.ForeignKey("Product", on_delete=models.CASCADE,related_name="product_offer",null=True,blank=True)
    category = models.ForeignKey("Category", on_delete=models.CASCADE,related_name="category_offer",null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.product:
            return f"Offer for {self.product.title}"
        elif self.category:
            return f"Offer for {self.category.name}"
        return f"Offer {self.id}"

    def apply_offer(self):
        """Apply the offer to all relevant product variants"""
        if not self.status == 'active':
            return

        variants = []
        if self.product:
            variants = self.product.variants.filter(is_delete=True)
        elif self.category:
            variants = ProductVariant.objects.filter(
                product__category=self.category,
                product__is_delete=True,
                is_delete=True
            )

        for variant in variants:
            original_price = variant.price
            if self.discount_type == 'percentage':
                new_discount_amount = (original_price * self.discount_value) / 100
            else:  # fixed amount
                new_discount_amount = self.discount_value

            if variant.is_offer:
            # Compare existing offer discount with the new one
                if new_discount_amount > variant.offer_discount:
                    # Apply the new offer if it's better
                    variant.offer_discount = new_discount_amount
                    variant.price_discount = original_price - new_discount_amount
            else:
                # Apply the offer as there is no existing offer
                variant.is_offer = True
                variant.offer_discount = new_discount_amount
                variant.price_discount = original_price - new_discount_amount

            variant.save()

    def remove_offer(self):
        """Remove the offer from all relevant product variants"""
        variants = []
        if self.product:
            variants = self.product.variants.filter(is_delete=True)
            print(variants)
        elif self.category:
            variants = ProductVariant.objects.filter(
                product__category=self.category,
                product__is_delete=True,
                is_delete=True
            )

        for variant in variants:
        # Remove current offer
            variant.is_offer = False
            variant.offer_discount = None
            variant.price_discount = None
            
            # Check for another applicable offer
            applicable_offers = Offer.objects.filter(
                status='active',
                product=variant.product
            ).exclude(id=self.id)

            if not applicable_offers.exists() and variant.product.category:
                print(variant.product.category)
                # Check for category-wide offers if no product-specific offer exists
                applicable_offers = Offer.objects.filter(
                    status='active',
                    category=variant.product.category
                ).exclude(id=self.id)
            print(applicable_offers)
            if applicable_offers.exists():
                # Apply the highest applicable offer
                
                best_offer = max(
                    applicable_offers,
                    key=lambda offer: (offer.discount_value if offer.discount_type == 'fixed' else (variant.price * offer.discount_value / 100))
                )

                original_price = variant.price
                if best_offer.discount_type == 'percentage':
                    discount_amount = (original_price * best_offer.discount_value) / 100
                else:  # fixed amount
                    discount_amount = best_offer.discount_value

                variant.is_offer = True
                variant.offer_discount = discount_amount
                variant.price_discount = original_price - discount_amount

            variant.save()

    def save(self, *args, **kwargs):
        if not self.pk or self._state.adding:
            # New offer being created
            super().save(*args, **kwargs)
            if self.status == 'active':
                self.apply_offer()
        else:
            # Existing offer being updated
            old_offer = Offer.objects.get(pk=self.pk)
            
            # First clear the old offer's effects
            if old_offer.status == 'active':
                # Get affected variants from old offer
                old_variants = []
                if old_offer.product:
                    old_variants = old_offer.product.variants.filter(is_delete=True)
                elif old_offer.category:
                    old_variants = ProductVariant.objects.filter(
                        product__category=old_offer.category,
                        product__is_delete=True,
                        is_delete=True
                    )
                
                # Clear old offer effects
                for variant in old_variants:
                    variant.is_offer = False
                    variant.offer_discount = None
                    variant.price_discount = None
                    variant.save()
            
            # Now save the new offer state
            super().save(*args, **kwargs)
            
            # Check if any relevant fields have changed
            fields_changed = (
                old_offer.status != self.status or
                old_offer.discount_type != self.discount_type or
                old_offer.discount_value != self.discount_value or
                old_offer.product != self.product or
                old_offer.category != self.category
            )
            
            # Apply new offer if needed
            if fields_changed and self.status == 'active':
                self.apply_offer()

class Wallet(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Wallet"
    
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('CREDIT', 'Credit'),
        ('DEBIT', 'Debit'),
    )


    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature_id = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Check if it's a new transaction
        is_new = self.pk is None

        super().save(*args, **kwargs)  # Save the transaction first to ensure integrity

        if is_new:  # Update wallet balance only for new transactions
            if self.transaction_type == 'CREDIT':
                self.wallet.balance += Decimal(self.amount) 
            elif self.transaction_type == 'DEBIT':
                self.wallet.balance -= Decimal(self.amount) 
            
            self.wallet.save() 

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.created_at}"

class ReturnRequest(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='return_requests')
    orderItem = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='return_requests_orderitem',null=True)
    user = models.ForeignKey('Users', on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),

    ], default='pending')
    return_received = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure return_received can only be True if status is 'approved'
        if self.return_received and self.status not in ['approved', 'completed']:
            raise ValueError("Return can only be marked as received if the status is 'approved' or 'completed'.")
        if self.return_received and self.status == 'approved':
            self.status = 'completed'

            self.add_order_amount_to_user()

            
            product_variant = self.orderItem.product_variant
            product_variant.available_quantity += self.orderItem.quantity
            product_variant.save()

        super(ReturnRequest, self).save(*args, **kwargs)
    
    def add_order_amount_to_user(self):
        """
        Add the refund amount for returned items to the user's wallet.
        """
        try:
            # Get or create the wallet for the user
            wallet = Wallet.objects.get(user=self.user)

            # Calculate the total refund amount based on returned items
            refund_amount = self.orderItem.total_price 
            

            # Create a wallet transaction for the refund
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=refund_amount,
                transaction_type='CREDIT',
                description=f"Refund for returned items in order {self.order.order_id}"
            )

            
        except Wallet.DoesNotExist:
            raise ValueError(f"Wallet does not exist for user {self.user.email}")
        except Exception as e:
            raise ValueError(f"Failed to update wallet balance: {str(e)}")
