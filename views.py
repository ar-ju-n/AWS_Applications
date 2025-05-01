from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Payment
import stripe
from django.conf import settings

@login_required
def create_payment(request, psychiatrist_id):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        psychiatrist = User.objects.get(id=psychiatrist_id)
        payment = Payment.objects.create(
            patient=request.user,
            psychiatrist=psychiatrist,
            amount=amount,
            status='pending'
        )
        return redirect('confirm_payment', payment_id=payment.id)
    return render(request, 'payment/create_payment.html')

@login_required
def confirm_payment(request, payment_id):
    payment = Payment.objects.get(id=payment_id)
    if request.method == 'POST':
        # Process payment with Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            charge = stripe.Charge.create(
                amount=int(payment.amount * 100),  # amount in cents
                currency='usd',
                source=request.POST['stripeToken'],
                description=f'Payment for session with {payment.psychiatrist.username}'
            )
            payment.status = 'completed'
            payment.save()
            return redirect('payment_success')
        except stripe.error.CardError as e:
            return render(request, 'payment/payment_error.html', {'error': e})
    return render(request, 'payment/confirm_payment.html', {'payment': payment}) 