from django.urls import path
from user.views import AccountDetail,ChangePassword,AddressDetail,SetAddressDefault,UpdateAddress,DeleteAddress,OrderListView,order_details_api,CancelOrder,WishlistView,download_invoice,ReturnOrderView,ReturnOrder,AddReturnOrder,completepayment

urlpatterns = [
    path('detail/',AccountDetail.as_view(),name='account'),
    path('change-password/',ChangePassword.as_view(),name='changepassword'),
    path('addres/detail',AddressDetail.as_view(),name="addressdetail"),
    path('set/addressdefault/<int:address_id>',SetAddressDefault.as_view(),name="set_default_address"),
    path('update/address',UpdateAddress.as_view(),name="updateaddress"),
    path('address/delete/<int:address_id>',DeleteAddress.as_view(),name="deleteaddress"),
    path('orderDeatail/',OrderListView.as_view(),name="userorderdetail"),
    path('orderDeatail/<uuid:uuid>/', order_details_api, name='order-details-api'),
    path('cancel/<uuid:uuid>/', CancelOrder.as_view(), name="cancelorder"),
    path('wishlist/', WishlistView.as_view(), name="wishlistview"),
    path('downloadinvoice/<uuid:uuid>/', download_invoice, name='download-invoice'),
    path('orders/<uuid:uuid>/return',ReturnOrder,name="return-order"),
    path('addretunorder/',AddReturnOrder,name="addretrunorder"),
    path('retunorder/',ReturnOrderView.as_view(),name="retrunorderview"),
    path('orders/payment/<uuid:uuid>/complete',completepayment,name="compeletepayment")

    

]
