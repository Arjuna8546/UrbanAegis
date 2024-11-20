from django.urls import path
from order.views import *

urlpatterns = [
    path('checkout/',Checkout.as_view(),name="checkout"),
    path('order/add',OrderAdd.as_view(),name="addorder")
]
