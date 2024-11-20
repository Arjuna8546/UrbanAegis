from django.urls import path
from core.views import RegisterView, VerifyOTPView,HomePageView, LoginView,ProductDetailView,CustomLogoutView,ProductListing,AccountInactive,QuantityView

urlpatterns = [
    
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verifyotp'),
    path('',HomePageView.as_view(),name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('product/<int:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('list/',ProductListing.as_view(),name='product_listing'),
    path('inactive/',AccountInactive.as_view(),name="inactive_account_page"),
    path('quantity/',QuantityView.as_view(),name="quantityview"),
    
]
