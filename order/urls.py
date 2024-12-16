from django.urls import path
from order.views import *

urlpatterns = [
    path('checkout/',Checkout.as_view(),name="checkout"),
    path('order/add',OrderAdd.as_view(),name="addorder"),
    path('apply-coupon/', apply_coupon, name='apply_coupon'),
    path('remove-coupon/', remove_coupon, name='remove_coupon'),
    path('verify-payment/', verify_payment, name='verify_payment'),
    path('verify/password/order',check_user_password,name='verify_order_password'),
    path('admin/returnview',OrderReturnAdminView.as_view(),name="adminorderreturnlist"),
    path('update-return-status/',updatereturnstatus,name="updateorderreturnstatus"),
    path('update-return-received/',updateReturnReceived,name="updateorderreturrecieved")
    
]
