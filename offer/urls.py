from django.urls import path
from . import views

urlpatterns = [
    path('', views.OfferListView.as_view(), name='offer_list'),
    path('add/', views.OfferCreateView.as_view(), name='add_offer'),
    path('<int:pk>/edit/', views.OfferUpdateView.as_view(), name='edit_offer'),
    path('<int:pk>/delete/', views.OfferDeleteView.as_view(), name='delete_offer'),
]