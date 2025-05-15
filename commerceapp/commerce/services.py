from abc import ABC, abstractmethod
import stripe
import uuid
import json
import hmac
import hashlib
import base64
import requests
from django.conf import settings
from django.utils import timezone
from .models import Payment


class PaymentProcessor(ABC):
    """Abstract base class for payment processors"""

    @abstractmethod
    def process_payment(self, payment, return_url=None):
        """Process the payment and return necessary data"""
        pass

    @abstractmethod
    def verify_payment(self, payment, transaction_id=None, payment_data=None):
        """Verify the payment status and update it"""
        pass


class CODPaymentProcessor(PaymentProcessor):
    """Cash on Delivery payment processor"""

    def process_payment(self, payment, return_url=None):
        """Process COD payment"""
        payment.status = 'processing'
        payment.transaction_id = f"COD-{uuid.uuid4().hex[:8]}"
        payment.save()

        return {
            'success': True,
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'message': 'Cash on delivery payment initialized',
            'redirect_url': None
        }

    def verify_payment(self, payment, transaction_id=None, payment_data=None):
        """Verify COD payment"""
        # For COD, payment is completed when order is delivered
        # This would typically be called by admin or delivery system
        payment.status = 'completed'
        payment.save()

        return {
            'success': True,
            'payment_id': payment.id,
            'status': payment.status,
            'message': 'Cash on delivery payment completed'
        }


class StripePaymentProcessor(PaymentProcessor):
    """Stripe payment processor"""

    def __init__(self):
        self.stripe_secret_key = settings.STRIPE_SECRET_KEY
        stripe.api_key = self.stripe_secret_key

    def process_payment(self, payment, return_url=None):
        """Process payment using Stripe"""
        try:
            # Create a payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'order_id': payment.order.id,
                    'payment_id': payment.id
                }
            )

            payment.transaction_id = intent.id
            payment.payment_details = {
                'client_secret': intent.client_secret,
                'payment_method_types': intent.payment_method_types,
            }
            payment.save()

            return {
                'success': True,
                'payment_id': payment.id,
                'transaction_id': payment.transaction_id,
                'client_secret': intent.client_secret,
                'payment_details': payment.payment_details,
                'redirect_url': None  # Frontend handles the redirect
            }

        except stripe.error.StripeError as e:
            payment.status = 'failed'
            payment.payment_details = {'error': str(e)}
            payment.save()

            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e),
                'redirect_url': None
            }

    def verify_payment(self, payment, transaction_id=None, payment_data=None):
        """Verify Stripe payment"""
        try:
            # Retrieve the payment intent
            intent = stripe.PaymentIntent.retrieve(payment.transaction_id)

            # Update payment status based on payment intent status
            if intent.status == 'succeeded':
                payment.status = 'completed'
            elif intent.status == 'processing':
                payment.status = 'processing'
            elif intent.status == 'canceled':
                payment.status = 'failed'

            payment.payment_details = {
                'stripe_status': intent.status,
                'payment_method': intent.payment_method,
                'receipt_url': intent.charges.data[0].receipt_url if intent.charges.data else None
            }
            payment.save()

            return {
                'success': True,
                'payment_id': payment.id,
                'status': payment.status,
                'message': f'Payment status updated to {payment.status}'
            }

        except stripe.error.StripeError as e:
            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e)
            }


class MomoPaymentProcessor(PaymentProcessor):
    """Momo payment processor"""

    def __init__(self):
        self.partner_code = settings.MOMO_PARTNER_CODE
        self.access_key = settings.MOMO_ACCESS_KEY
        self.secret_key = settings.MOMO_SECRET_KEY
        self.api_endpoint = settings.MOMO_API_ENDPOINT

    def _create_signature(self, data):
        """Create HMAC SHA256 signature for Momo"""
        data_str = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
        h = hmac.new(
            self.secret_key.encode(),
            data_str.encode(),
            hashlib.sha256
        )
        return h.hexdigest()

    def process_payment(self, payment, return_url=None):
        """Process payment using Momo"""
        if not return_url:
            return {
                'success': False,
                'message': 'Return URL is required for Momo payments'
            }

        try:
            # Create payment request data
            request_id = str(uuid.uuid4())
            order_id = f"MOMO-{payment.order.id}-{int(timezone.now().timestamp())}"
            request_data = {
                'partnerCode': self.partner_code,
                'accessKey': self.access_key,
                'requestId': request_id,
                'amount': str(int(payment.amount)),
                'orderId': order_id,
                'orderInfo': f'Payment for order {payment.order.id}',
                'returnUrl': return_url,
                'notifyUrl': settings.MOMO_NOTIFY_URL,
                'extraData': base64.b64encode(json.dumps({
                    'payment_id': payment.id
                }).encode()).decode()
            }

            # Create signature
            request_data['signature'] = self._create_signature(request_data)

            # Send request to Momo
            response = requests.post(
                f"{self.api_endpoint}/create",
                json=request_data
            )
            response_data = response.json()

            if response_data.get('errorCode') == 0:
                payment.transaction_id = order_id
                payment.payment_details = {
                    'request_id': request_id,
                    'payment_url': response_data.get('payUrl'),
                    'momo_response': response_data
                }
                payment.save()

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'redirect_url': response_data.get('payUrl'),
                    'payment_details': payment.payment_details
                }
            else:
                payment.status = 'failed'
                payment.payment_details = {'error': response_data}
                payment.save()

                return {
                    'success': False,
                    'payment_id': payment.id,
                    'message': response_data.get('message', 'Unknown error')
                }

        except Exception as e:
            payment.status = 'failed'
            payment.payment_details = {'error': str(e)}
            payment.save()

            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e)
            }

    def verify_payment(self, payment, transaction_id=None, payment_data=None):
        """Verify Momo payment"""
        try:
            # Create query request data
            request_id = str(uuid.uuid4())
            request_data = {
                'partnerCode': self.partner_code,
                'accessKey': self.access_key,
                'requestId': request_id,
                'orderId': payment.transaction_id,
                'requestType': 'transactionStatus'
            }

            # Create signature
            request_data['signature'] = self._create_signature(request_data)

            # Send request to Momo
            response = requests.post(
                f"{self.api_endpoint}/query",
                json=request_data
            )
            response_data = response.json()

            if response_data.get('errorCode') == 0:
                # Update payment status based on Momo response
                if response_data.get('transactionStatus') == 0:
                    payment.status = 'completed'
                elif response_data.get('transactionStatus') == 1:
                    payment.status = 'processing'
                else:
                    payment.status = 'failed'

                payment.payment_details = {
                    **payment.payment_details,
                    'transaction_status': response_data.get('transactionStatus'),
                    'message': response_data.get('message'),
                    'pay_type': response_data.get('payType'),
                    'response_time': response_data.get('responseTime')
                }
                payment.save()

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'status': payment.status,
                    'message': f'Payment status updated to {payment.status}'
                }
            else:
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'message': response_data.get('message', 'Unknown error')
                }

        except Exception as e:
            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e)
            }


class ZaloPayPaymentProcessor(PaymentProcessor):
    """ZaloPay payment processor"""

    def __init__(self):
        self.app_id = settings.ZALOPAY_APP_ID
        self.key1 = settings.ZALOPAY_KEY1
        self.key2 = settings.ZALOPAY_KEY2
        self.api_endpoint = settings.ZALOPAY_API_ENDPOINT

    def _create_signature(self, data, key):
        """Create HMAC SHA256 signature for ZaloPay"""
        data_str = ""
        for key in sorted(data.keys()):
            data_str += f"{key}={data[key]}"

        h = hmac.new(key.encode(), data_str.encode(), hashlib.sha256)
        return h.hexdigest()

    def process_payment(self, payment, return_url=None):
        """Process payment using ZaloPay"""
        if not return_url:
            return {
                'success': False,
                'message': 'Return URL is required for ZaloPay payments'
            }

        try:
            # Create app transaction ID
            app_trans_id = f"{self.app_id}_{int(timezone.now().timestamp())}"

            # Create payment request data
            embed_data = json.dumps({
                'payment_id': payment.id,
                'order_id': payment.order.id,
                'redirecturl': return_url
            })

            request_data = {
                'app_id': self.app_id,
                'app_trans_id': app_trans_id,
                'app_user': f"user_{payment.order.user.id}" if hasattr(payment.order, 'user') else "anonymous",
                'app_time': int(timezone.now().timestamp()),
                'amount': int(payment.amount),
                'item': json.dumps([{
                    'id': f'item_{payment.order.id}',
                    'name': f'Payment for order {payment.order.id}',
                    'price': int(payment.amount),
                    'quantity': 1
                }]),
                'description': f'Payment for order {payment.order.id}',
                'embed_data': embed_data,
                'bank_code': 'zalopayapp',
            }

            # Create signature
            request_data['mac'] = self._create_signature(request_data, self.key1)

            # Send request to ZaloPay
            response = requests.post(
                f"{self.api_endpoint}/create",
                json=request_data
            )
            response_data = response.json()

            if response_data.get('return_code') == 1:
                payment.transaction_id = app_trans_id
                payment.payment_details = {
                    'app_trans_id': app_trans_id,
                    'order_url': response_data.get('order_url'),
                    'zalo_response': response_data
                }
                payment.save()

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'redirect_url': response_data.get('order_url'),
                    'payment_details': payment.payment_details
                }
            else:
                payment.status = 'failed'
                payment.payment_details = {'error': response_data}
                payment.save()

                return {
                    'success': False,
                    'payment_id': payment.id,
                    'message': response_data.get('return_message', 'Unknown error')
                }

        except Exception as e:
            payment.status = 'failed'
            payment.payment_details = {'error': str(e)}
            payment.save()

            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e)
            }

    def verify_payment(self, payment, transaction_id=None, payment_data=None):
        """Verify ZaloPay payment"""
        try:
            # Create query request data
            request_data = {
                'app_id': self.app_id,
                'app_trans_id': payment.transaction_id,
            }

            # Create signature
            request_data['mac'] = self._create_signature(request_data, self.key1)

            # Send request to ZaloPay
            response = requests.post(
                f"{self.api_endpoint}/query",
                json=request_data
            )
            response_data = response.json()

            if response_data.get('return_code') == 1:
                # Update payment status based on ZaloPay response
                if response_data.get('return_code') == 1:
                    payment.status = 'completed'
                elif response_data.get('return_code') == 2:
                    payment.status = 'processing'
                else:
                    payment.status = 'failed'

                payment.payment_details = {
                    **payment.payment_details,
                    'zalo_trans_id': response_data.get('zp_trans_id'),
                    'trans_time': response_data.get('trans_time'),
                    'return_message': response_data.get('return_message')
                }
                payment.save()

                return {
                    'success': True,
                    'payment_id': payment.id,
                    'status': payment.status,
                    'message': f'Payment status updated to {payment.status}'
                }
            else:
                return {
                    'success': False,
                    'payment_id': payment.id,
                    'message': response_data.get('return_message', 'Unknown error')
                }

        except Exception as e:
            return {
                'success': False,
                'payment_id': payment.id,
                'message': str(e)
            }


class PaymentFactory:
    """Factory class for creating payment processors"""

    @staticmethod
    def get_processor(payment_method):
        """Get the appropriate payment processor based on the method"""
        processors = {
            'cod': CODPaymentProcessor,
            'stripe': StripePaymentProcessor,
            'momo': MomoPaymentProcessor,
            'zalopay': ZaloPayPaymentProcessor,
        }

        processor_class = processors.get(payment_method)
        if not processor_class:
            raise ValueError(f"Unsupported payment method: {payment_method}")

        return processor_class()