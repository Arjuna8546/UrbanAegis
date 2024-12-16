from django.http import JsonResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear, TruncWeek
from datetime import timedelta
from django.utils.timezone import now, make_aware
from core.models import Order

def get_order_data(request):
    filter_type = request.GET.get('filter', 'daily')  # Default to 'daily'

    if filter_type == 'daily':
        date_trunc = TruncDay('created_at')
        start_date = now() - timedelta(days=7)  # Use `now()` to get timezone-aware datetime
    elif filter_type == 'weekly':
        date_trunc = TruncWeek('created_at')
        start_date = now() - timedelta(weeks=4)
    elif filter_type == 'monthly':
        date_trunc = TruncMonth('created_at')
        start_date = now().replace(day=1) - timedelta(days=30)
    elif filter_type == 'yearly':
        date_trunc = TruncYear('created_at')
        start_date = now().replace(month=1, day=1)
    else:
        return JsonResponse({'error': 'Invalid filter type'}, status=400)
    
    if not start_date.tzinfo:
        start_date = make_aware(start_date)

    # Filter and annotate data
    order_data = (
        Order.objects.filter(created_at__gte=start_date)
        .annotate(date=date_trunc)
        .values('date')
        .annotate(
            total_sales=Sum('total_amount'),
            orders_count=Count('id')
        )
        .order_by('date')
    )

    # Format data for JSON response
    data = {
        'labels': [entry['date'].strftime('%Y-%m-%d') for entry in order_data],
        'totals': [entry['total_sales'] for entry in order_data],
        'orders_count': [entry['orders_count'] for entry in order_data],
    }

    return JsonResponse(data)

def get_payment_methods(request):
    payment_methods_data = Order.objects.values('payment_method').annotate(count=Count('id'))
    data = {entry['payment_method']: entry['count'] for entry in payment_methods_data}
    return JsonResponse(data)