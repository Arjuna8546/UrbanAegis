from django.urls import path
from coupon.views import *

urlpatterns = [
    path('', CouponListView.as_view(), name='admin-coupons'),
    path('add/', CouponCreateView.as_view(), name='admin-coupon-add'),
    path('<int:pk>/edit/', CouponUpdateView.as_view(), name='admin-coupon-edit'),
    path('<int:pk>/delete/', CouponDeleteView.as_view(), name='admin-coupon-delete'),

]
