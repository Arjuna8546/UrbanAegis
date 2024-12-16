from django.urls import path
from cart.views import AddCart,remove_cart_item,update_cart_item_quantity,add_to_cart_modal

urlpatterns = [
    path('',AddCart.as_view(),name="addcart"),
    path('remove/<int:id>/', remove_cart_item, name='remove_cart_item'),
    path('update/<int:id>/', update_cart_item_quantity, name='update_cart_item_quantity'),
    path('add-modal/', add_to_cart_modal, name='add_to_cart_modal'),
    
]
