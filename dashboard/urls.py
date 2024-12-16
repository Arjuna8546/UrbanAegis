from django.urls import path
from .views import *

urlpatterns = [
    path('get-order-data/',get_order_data,name="dashboard"),
    path('get_payment_methods/',get_payment_methods,name="dashboardpie")
]
