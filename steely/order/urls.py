from django.urls import path
from order.views import *

urlpatterns = [
    path('checkout/',Checkout.as_view(),name="checkout"),
    path('order/add',OrderAdd.as_view(),name="addorder"),
    path('apply-coupon/', apply_coupon, name='apply_coupon'),
    path('remove-coupon/', remove_coupon, name='remove_coupon'),
    path('create-order/', create_order, name='create_order'),
    path('verify-payment/', verify_payment, name='verify_payment'),
    path('success/',order_succsess.as_view(),name="order_sucsses")
]
