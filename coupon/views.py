from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from core.models import Coupon
from .forms import CouponForm

# Create your views here.
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser
    
class CouponListView(AdminRequiredMixin, ListView):
    model = Coupon
    template_name = 'admin_coupon.html'
    context_object_name = 'coupons'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(code__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(status__icontains=search_query)
            )
        return queryset

    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' and \
           self.request.GET.get('table_only'):
            return ['admin_coupons_table.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not (self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' and \
                self.request.GET.get('table_only')):
            context['form'] = CouponForm()
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CouponForm()  # Add form for creating new coupon
        return context

class CouponCreateView(AdminRequiredMixin, CreateView):
    model = Coupon
    form_class = CouponForm
    template_name = 'admin_coupon.html'
    success_url = reverse_lazy('admin-coupons')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Coupon {self.object.code} has been created successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Error creating coupon. Please check the form.')
        return self.render_to_response(self.get_context_data(form=form))

class CouponUpdateView(AdminRequiredMixin, UpdateView):
    model = Coupon
    form_class = CouponForm
    template_name = 'admin_coupon.html'
    success_url = reverse_lazy('admin-coupons')

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            coupon = self.get_object()
            data = {
                'code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': str(coupon.discount_value),
                'min_purchase': str(coupon.min_purchase),
                'valid_from': coupon.valid_from.isoformat(),
                'valid_until': coupon.valid_until.isoformat(),
                'usage_limit': coupon.usage_limit,
                'status': coupon.status,
                'description': coupon.description,
            }
            return JsonResponse(data)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Coupon {self.object.code} has been updated successfully.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Error updating coupon. Please check the form.')
        return super().form_invalid(form)

class CouponDeleteView(AdminRequiredMixin, DeleteView):
    model = Coupon
    success_url = reverse_lazy('admin-coupons')
    template_name = 'admin_coupon.html'  # You can also create a separate confirm_delete.html if needed

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, f'Coupon {self.object.code} has been deleted successfully.')
        except Exception as e:
            messages.error(request, 'Error deleting coupon.')
        return HttpResponseRedirect(self.success_url)

