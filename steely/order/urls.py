from django.urls import path
from order.views import *

urlpatterns = [
    path('checkout/',Checkout.as_view(),name="checkout")
]
