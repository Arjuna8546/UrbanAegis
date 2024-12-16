from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import  UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from core.models import Offer
from .forms import OfferForm

class StaffRequiredMixin(UserPassesTestMixin):
    login_url = 'admin_login'
    def test_func(self):
        return self.request.user.is_staff

class OfferListView( StaffRequiredMixin, ListView):
    model = Offer
    template_name = 'offer.html'
    context_object_name = 'offers'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = OfferForm()
        context['title'] = 'Manage Offers'
        context['section'] = 'offers'
        return context

class OfferCreateView( StaffRequiredMixin, CreateView):
    model = Offer
    form_class = OfferForm
    template_name = 'offer.html'    
    success_url = reverse_lazy('offer_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Offer created successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error creating offer. Please check the form.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offers'] = Offer.objects.all()
        context['title'] = 'Manage Offers'
        context['section'] = 'offers'
        return context

class OfferUpdateView( StaffRequiredMixin, UpdateView):
    model = Offer
    form_class = OfferForm
    template_name = 'offer.html'
    success_url = reverse_lazy('offer_list')
    
    def form_valid(self, form):
        old_status = self.get_object().status
        response = super().form_valid(form)
        # The offer's save method will handle applying/removing the offer based on status change
        messages.success(self.request, 'Offer updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error updating offer. Please check the form.')
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offers'] = Offer.objects.all()
        context['title'] = 'Edit Offer'
        context['section'] = 'offers'
        return context

class OfferDeleteView( StaffRequiredMixin, DeleteView):
    model = Offer
    success_url = reverse_lazy('offer_list')
    
    def delete(self, request, *args, **kwargs):
        offer = self.get_object()
        # Remove the offer from variants before deleting
        offer.remove_offer()
        messages.success(self.request, 'Offer deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)
