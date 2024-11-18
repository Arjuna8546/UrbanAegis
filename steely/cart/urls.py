from django.urls import path
from cart.views import AddCart

urlpatterns = [
    path('',AddCart.as_view(),name="addcart"),
]
