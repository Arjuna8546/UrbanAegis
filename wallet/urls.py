from django.urls import path
from .views import WalletView,walletaddintialize,verify_payment,ActivateWallet,DeactivateWallet

urlpatterns = [
    path('',WalletView.as_view(),name="wallet"),
    path('addmoney/',walletaddintialize,name="addmoney"),
    path('verifywalletadd/',verify_payment,name="verify_payment_wallet"),
    path('activate/wallet',ActivateWallet.as_view(),name="activate"),
    path('deactivate/wallet',DeactivateWallet.as_view(),name="deactivate")
    


]
