from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
import base64

from .models import Payment
from .services import PaymentFactory


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not sig_header:
        return HttpResponse('No signature header', status=400)

    try:
        import stripe
        from django.conf import settings

        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']

            # Find the payment
            order_id = payment_intent['metadata']['order_id']
            payment_id = payment_intent['metadata']['payment_id']

            payment = Payment.objects.get(id=payment_id, order__id=order_id)

            # Update payment status
            processor = PaymentFactory.get_processor('stripe')
            processor.verify_payment(payment)

        # Add other event types as needed

        return HttpResponse(status=200)

    except Exception as e:
        return HttpResponse(str(e), status=400)


@csrf_exempt
def momo_webhook(request):
    """Handle Momo webhook events"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Extract payment_id from extraData
            extra_data = json.loads(base64.b64decode(data.get('extraData', '')).decode())
            payment_id = extra_data.get('payment_id')

            if payment_id:
                payment = Payment.objects.get(id=payment_id)

                # Verify the signature
                from django.conf import settings

                # Build signature data
                signature_data = {
                    'partnerCode': data.get('partnerCode'),
                    'accessKey': data.get('accessKey'),
                    'requestId': data.get('requestId'),
                    'amount': data.get('amount'),
                    'orderId': data.get('orderId'),
                    'orderInfo': data.get('orderInfo'),
                    'orderType': data.get('orderType'),
                    'transId': data.get('transId'),
                    'errorCode': data.get('errorCode'),
                    'message': data.get('message'),
                    'localMessage': data.get('localMessage'),
                    'payType': data.get('payType'),
                    'responseTime': data.get('responseTime'),
                    'extraData': data.get('extraData')
                }

                # Create HMAC SHA256 signature
                import hmac
                import hashlib

                data_str = "&".join([f"{k}={v}" for k, v in sorted(signature_data.items())])
                h = hmac.new(
                    settings.MOMO_SECRET_KEY.encode(),
                    data_str.encode(),
                    hashlib.sha256
                )
                signature = h.hexdigest()

                # Verify signature
                if signature == data.get('signature'):
                    # Update payment status
                    processor = PaymentFactory.get_processor('momo')
                    processor.verify_payment(payment)

                    return HttpResponse('success', status=200)

            return HttpResponse('Invalid data', status=400)

        except Exception as e:
            return HttpResponse(str(e), status=400)

    return HttpResponse('Method not allowed', status=405)


@csrf_exempt
def zalopay_webhook(request):
    """Handle ZaloPay webhook events"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Extract payment_id from embed_data
            embed_data = json.loads(data.get('embed_data', '{}'))
            payment_id = embed_data.get('payment_id')

            if payment_id:
                payment = Payment.objects.get(id=payment_id)

                # Verify the signature
                from django.conf import settings
                import hmac
                import hashlib

                # Build data string for MAC verification
                data_str = f"{data.get('app_id')}|{data.get('app_trans_id')}|{data.get('app_user')}|{data.get('amount')}|" \
                           f"{data.get('app_time')}|{data.get('embed_data')}|{data.get('item')}"

                # Create HMAC SHA256 signature
                h = hmac.new(
                    settings.ZALOPAY_KEY2.encode(),
                    data_str.encode(),
                    hashlib.sha256
                )
                mac = h.hexdigest()

                # Verify MAC
                if mac == data.get('mac'):
                    # Update payment status
                    processor = PaymentFactory.get_processor('zalopay')
                    processor.verify_payment(payment)

                    # Return success response
                    return HttpResponse(json.dumps({
                        'return_code': 1,
                        'return_message': 'success'
                    }), content_type='application/json')

            return HttpResponse(json.dumps({
                'return_code': 0,
                'return_message': 'Invalid data'
            }), content_type='application/json', status=400)

        except Exception as e:
            return HttpResponse(json.dumps({
                'return_code': 0,
                'return_message': str(e)
            }), content_type='application/json', status=400)

    return HttpResponse('Method not allowed', status=405)
