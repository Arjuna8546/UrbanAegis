from django.urls import path
from cart.views import AddCart,remove_cart_item,update_cart_item_quantity

urlpatterns = [
    path('',AddCart.as_view(),name="addcart"),
    path('remove/<int:id>/', remove_cart_item, name='remove_cart_item'),
    path('update/<int:id>/', update_cart_item_quantity, name='update_cart_item_quantity'),
]
