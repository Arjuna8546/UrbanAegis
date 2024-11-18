from django.urls import path
from user.views import AccountDetail,ChangePassword,AddressDetail,SetAddressDefault,UpdateAddress,DeleteAddress

urlpatterns = [
    path('detail/',AccountDetail.as_view(),name='account'),
    path('change-password/',ChangePassword.as_view(),name='changepassword'),
    path('addres/detail',AddressDetail.as_view(),name="addressdetail"),
    path('set/addressdefault/<int:address_id>',SetAddressDefault.as_view(),name="set_default_address"),
    path('update/address',UpdateAddress.as_view(),name="updateaddress"),
    path('address/delete/<int:address_id>',DeleteAddress.as_view(),name="deleteaddress"),
    

]
