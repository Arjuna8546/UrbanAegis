from django.urls import path
from core.views import RegisterView, VerifyOTPView,HomePageView, LoginView,ProductDetailView,CustomLogoutView,AccountInactive,QuantityView,ProductShow,ProductListView,FilteredProductList,toggle_wishlist

urlpatterns = [
    
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verifyotp'),
    path('',HomePageView.as_view(),name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('product/<int:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('inactive/',AccountInactive.as_view(),name="inactive_account_page"),
    path('quantity/',QuantityView.as_view(),name="quantityview"),
    path('product/list/',ProductShow.as_view(),name="productgetting"),
    path('product/list-page',ProductListView.as_view(),name="productpagelist"),
    path('product/list/filter/', FilteredProductList.as_view(), name="filter_products"),
    path('wishlist/toggle/', toggle_wishlist, name='toggle_wishlist'),
    
    
]
