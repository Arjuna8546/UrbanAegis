from django.urls import path
from user.views import AccountDetail,ChangePassword,AddressDetail

urlpatterns = [
    path('detail/',AccountDetail.as_view(),name='account'),
    path('change-password/',ChangePassword.as_view(),name='changepassword'),
    path('addres/detail',AddressDetail.as_view(),name="addressdetail")
]
