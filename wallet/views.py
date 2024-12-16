from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render,redirect,HttpResponse,get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from razorpay import Client
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.contrib.auth.mixins import LoginRequiredMixin
from core.models import Wallet,WalletTransaction
from django.contrib import messages

class WalletView(LoginRequiredMixin, View):
    template_name = 'wallet.html'

    def get(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user)
            if not wallet.is_active:
                # Redirect to the wallet activation page if the wallet is inactive
                messages.warning(request, "Your wallet is inactive. Please activate it to access wallet features.")
                return redirect('activate')
        except Wallet.DoesNotExist:
            # Redirect to wallet activation if no wallet exists
            messages.warning(request, "No wallet found. Please activate your wallet.")
            return redirect('activate')
        transactions = wallet.transactions.all().order_by('-created_at')
        
        context = {
            'wallet': wallet,
            'transactions': transactions
        }
        return render(request, self.template_name, context)

class ActivateWallet(LoginRequiredMixin, View):
    template_name = 'activate_wallet.html'

    def get(self, request):
        # Render the wallet activation page
        return render(request, self.template_name)
    def post(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        if not wallet.is_active:
            wallet.is_active = True
            wallet.save()
            messages.success(request, "Wallet activated successfully!")
        return redirect('wallet')
class DeactivateWallet(LoginRequiredMixin, View):
    def post(self, request):
        try:
            wallet = Wallet.objects.get(user=request.user, is_active=True)
            wallet.is_active = False
            wallet.save()
            messages.success(request, "Wallet deactivated successfully!")
        except Wallet.DoesNotExist:
            messages.error(request, "No active wallet found to deactivate.")
        return redirect('activate')


@csrf_exempt
def walletaddintialize(request):
    if request.method == "POST":
            import json
            data = json.loads(request.body)

            amount = data.get("amount")
            if not amount or int(amount) <= 0:
                return JsonResponse({"success": False, "message": "Invalid amount"}, status=400)

            # Initialize Razorpay client
            client = Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Create an order
            try:
                amount_in_paise = int(float(amount) * 100)
                order_data = {
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "payment_capture": 1
                }
                
                razorpay_order = client.order.create(data=order_data)

            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)}, status=500)

            return JsonResponse({
                "success": True,
                "razorpay_order_id": razorpay_order.get("id"),
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": amount
            })

    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)

        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        amount =  data.get("amount")
        

        if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
            return JsonResponse({"success": False, "message": "Missing payment details"}, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            # Verify the signature
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature
            })

            wallet = get_object_or_404(Wallet,user= request.user)

            wallettransaction =WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                transaction_type="CREDIT",
                razorpay_order_id=razorpay_order_id,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature_id=razorpay_signature,
                description="razorpay"
            )

            return JsonResponse({"success": True, "message": "Payment verified successfully"})
        except razorpay.errors.SignatureVerificationError as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)