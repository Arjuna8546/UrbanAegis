from django.urls import path
from core.views import RegisterView, VerifyOTPView,HomePageView, LoginView,ProductDetailView,CustomLogoutView,AccountInactive,QuantityView,toggle_wishlist,PasswordResetView,VerifyOTPViewForget,SetNewPasswordView,ProductGridList

urlpatterns = [
    
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verifyotp'),
    path('',HomePageView.as_view(),name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('product/<int:product_id>/', ProductDetailView.as_view(), name='product_detail'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('inactive/',AccountInactive.as_view(),name="inactive_account_page"),
    path('quantity/',QuantityView.as_view(),name="quantityview"),
    # path('product/list-page',ProductListView.as_view(),name="productpagelist"),
    # path('product/list/filter/', FilteredProductList.as_view(), name="filter_products"),
    path('wishlist/toggle/', toggle_wishlist, name='toggle_wishlist'),
    path('forgetpassword/', PasswordResetView.as_view(), name='forgetpassword'),
    path('verify-otp/forget/', VerifyOTPViewForget.as_view(), name='verifyotpforget'),
    path('set-new-password/', SetNewPasswordView.as_view(), name='set_new_password'),
    
    path('allproduct/',ProductGridList.as_view(),name="allproductshow"),
    path('ajax/load-all-products/', ProductGridList.as_view(), name='load_all_products'),
]
