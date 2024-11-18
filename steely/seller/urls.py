from django.urls import path
from seller.views import AdminLoginView,AdminDashboardView,AdminCoustomersView,ProductListView,ProductCreateView,CategoryView,ProductVariantUpdateView,ChooseDeleteProductOrVariantView,ConfirmDeleteProductOrVariantView,ToggleActiveStatusView,ToggleCategoryStatusView,AdminLogOutView
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('',AdminLoginView.as_view(),name="admin_login"),
    path('admin/logout/',AdminLogOutView.as_view(),name="admin_logout"),
    path('dashboard/',AdminDashboardView.as_view(),name="admin_dashboard"),
    path('coustomers/',AdminCoustomersView.as_view(),name="coustomers"),
    path('product/',ProductListView.as_view(),name="product"),
    path('add-product/',ProductCreateView.as_view(),name="add_product"),
    path('categorie/',CategoryView.as_view(),name="categorie"),
    path('variant/update/<int:pk>/', ProductVariantUpdateView.as_view(), name='update_variant'),
    path('delete/choose/<int:variant_id>/', ChooseDeleteProductOrVariantView.as_view(), name='choose_delete_product_or_variant'),
    path('delete/confirm/<int:variant_id>/<str:entity_type>/', ConfirmDeleteProductOrVariantView.as_view(), name='confirm_delete_product_or_variant'),
    path('toggle-active-status/<int:user_id>/', ToggleActiveStatusView.as_view(), name='toggle_active_status'),
    path('categories/toggle/<int:category_id>/', ToggleCategoryStatusView.as_view(), name='toggle_category_status'),
     
]
    
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)