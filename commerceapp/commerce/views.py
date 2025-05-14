import hashlib
import json
import uuid
from datetime import time
from gc import get_objects
from pickle import FALSE
from urllib.request import Request
# from tarfile import TruncatedHeaderError
from xmlrpc.client import ResponseError

from cryptography.hazmat.primitives import hmac
from django.contrib.auth.decorators import login_required
from django.contrib.sites import requests
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import viewsets, permissions, generics, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from rest_framework.serializers import ValidationError
from unicodedata import category

from .models import Category, Product, Comment, User, Role, Shop, ShopProduct, Payment, PaymentMethod
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer, UserSerializer, ShopSerializer, ShopProductSerializer
from . import serializers, paginator
from . import permission
from ..commerceapp import settings


def index(request):
    return HttpResponse("E-commerce")

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(active=True)
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "destroy", "update", "partial_update"]:
            return [permission.IsAdminOrStaff()]
        return [permissions.AllowAny()]

    @action(methods=['get'], url_path='products', detail=True)
    def get_products(self, request, pk):
        product = self.get_object().products.filter(active=True)
        p = paginator.ProductPaginator()
        page = p.paginate_queryset(product, self.request)
        if page:
            s = ProductSerializer(page, many=True)
            return p.get_paginated_response(s.data)
        else:
            return Response(ProductSerializer(product, many=True).data, status.HTTP_200_OK )

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(active=True)
    serializer_class = serializers.ProductSerializer
    pagination_class = paginator.ItemPaginator

    def get_permissions(self):
        if self.action.__eq__('get_comments') and self.request.method.__eq__('POST'):
            return [permissions.IsAuthenticated()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permission.IsSeller()]
        return [AllowAny()]

    def get_queryset(self):
        query = self.queryset
        #tim san pham theo ten
        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)

        #tim san pham theo danh muc
        cate_id = self.request.query_params.get('cate_id')
        if cate_id:
            query = query.filter(category_id = cate_id)
        return query

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


    @action(methods=['get', 'post'], url_path="comment", detail=True)
    def get_comments(self, request, pk):
        if request.method.__eq__('POST'):
            c = Comment.objects.create(content=request.data.get('content'),
                                       product=self.get_object(),
                                       user=request.user)
            return Response(CommentSerializer(c).data, status=status.HTTP_201_CREATED)
        else:
            comments = self.get_object().comment_set.select_related('user').filter(active=True).order_by('-id')
            p = paginator.ProductPaginator()
            page = p.paginate_queryset(comments, self.request)
            if page:
                c = CommentSerializer(page, many=True)
                return p.get_paginated_response(c.data)
            else:
                return Response(CommentSerializer(comments, many = True).data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [parsers.MultiPartParser]


    def register_user(self, request, role_name, is_staff=False):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            role = Role.objects.get(name=role_name)
            user.role = role
            user.is_staff= is_staff
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    #Đăng kí người mua
    @action(methods=['post'], detail=False, url_path='register-buyer' )
    def register_buyer(self, request):
        return self.register_user(request, role_name="buyer")


    #Đăng kí người bán
    @action(methods=['post'], detail=False, url_path='register-seller')
    def register_seller(self, request):
        return self.register_user(request, role_name="seller")


    #đăng kí thêm tài khoảng cho nhân viên
    @action(methods=['post'], detail=False, url_path='register-staff', permission_classes=[permission.IsAdmin])
    def register_staff(self, request):
        return self.register_user(request, role_name="staff", is_staff=True )


    #Đăng kí tài khoản là admin của hệ thống
    @action(methods=['post'], detail=False, url_path='register-admin', permission_classes=[permission.IsSuperUser])
    def register_admin(self, request):
        return self.register_user(request, role_name="admin", is_staff=True)


    #Lấy danh sách người dùng là seller đang chờ duyệt
    @action(methods=['get'], url_path='pending-seller', detail=False, permission_classes=[permission.IsAdminOrStaff])
    def get_pending_seller(self, request):
        role = Role.objects.get(name='seller')
        pending_user = User.objects.filter(is_verified_seller=False, role=role)
        return Response(UserSerializer(pending_user, many=True).data, status=status.HTTP_200_OK)

    # Duyệt / hủy quyền người bán
    @action(methods=['patch'], detail=True, url_path="verify-seller",
            permission_classes=[permission.IsAdminOrStaff])
    def verify_seller(self, request, pk):
        try:
            user = User.objects.get(pk=pk)  # Lấy user từ pk
            user.is_verified_seller = True
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(methods=['patch'], detail=True, url_path="cancel-seller",
            permission_classes=[permission.IsAdminOrStaff])
    def cancel_seller(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            user.is_verified_seller = False
            user.save()
            return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
        except:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


    # Lấy người dùng hiện tại
    @action(methods=['get', 'patch'], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_current_user(self, request):
        if request.method.__eq__("PATCH"):
            u = request.user
            for key in request.data:
                if key in ['first_name', 'last_name', 'avatar', 'phone']:
                    setattr(u, key, request.data[key])
                elif key.__eq__('password'):
                    u.set_password(request.data[key])
            u.save()
            return Response(UserSerializer(u).data)
        else:
            return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.filter(active=True)
    serializer_class = ShopSerializer
    def get_permissions(self):
        if self.action in ["create", "update", "destroy", "update", "partial_update"]:
            return [permission.IsAdminOrSeller()]
        return [permissions.AllowAny()]

    #gan user dang nhap la chu shop
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        # Kiểm tra nếu không phải admin thì phải là chủ shop mới được cập nhật
        if self.request.user != self.get_object().user and not self.request.user.is_superuser:
            raise PermissionDenied("Bạn không có quyền chỉnh sửa shop này!")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user != instance.user and not self.request.user.is_superuser:
            raise PermissionDenied("Bạn không có quyền xóa shop này!")
        instance.delete()


class ShopProductViewSet(viewsets.ModelViewSet):
    queryset = ShopProduct.objects.filter(active=True)
    serializer_class = ShopProductSerializer
    permission_classes = [permission.IsSeller]

    def get_queryset(self):

        #Chỉ trả về ShopProduct thuộc về shop của người bán hiện tại.
        user = self.request.user
        shop = getattr(user, 'shop', None)
        if not shop:
            return ShopProduct.objects.none()
        return ShopProduct.objects.filter(shop=shop, active=True)

    def perform_create(self, serializer):
        #Gán shop tự động từ user và gọi serializer.save().
        user = self.request.user
        shop = getattr(user, 'shop', None)

        if not shop:
            raise ValidationError("Người dùng chưa có shop để tạo sản phẩm.")
        serializer.save(shop=shop)


class PaymentViewSet(viewsets.ModelViewSet):
    def process_cod_payment(request, payment, order):
        pass

    def process_paypal_payment(request, payment, order):
        pass

    def process_stripe_payment(request, payment, order):
        pass

    def process_momo_payment(request, payment, order):
        pass

    def process_zalopay_payment(request, payment, order):
        pass

    #View chọn phương thức thanh toán
    @login_required
    def payment_selection(request, order_id):
        order = get_object_or_404('commerce_order.Order', id=order_id,
                                  user=request.user)  # Match your actual app and model names
        payment_methods = PaymentMethod.objects.filter(is_active=True)

        return render(request, 'payments/select_payment.html', {
            'order': order,
            'payment_methods': payment_methods
        })

    # Process payment based on selected method
    @login_required
    def process_payment(request, order_id):
        """
        Process payment based on the selected payment method
        """
        if request.method != 'POST':
            return redirect('payment_selection', order_id=order_id)

        order = get_object_or_404('commerce_order.Order', id=order_id, user=request.user)  # Match your model
        payment_method_id = request.POST.get('payment_method')
        payment_method = get_object_or_404(PaymentMethod, id=payment_method_id)

        # Create initial payment record
        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,  # Ensure this field exists in your Order model
            payment_method=payment_method,
            status='PENDING'
        )

        # Process payment based on method
        if payment_method.name == 'COD':
            return request.process_cod_payment(request, payment, order)
        elif payment_method.name == 'PAYPAL':
            return request.process_paypal_payment(request, payment, order)
        elif payment_method.name == 'STRIPE':
            return request.process_stripe_payment(request, payment, order)
        elif payment_method.name == 'MOMO':
            return request.process_momo_payment(request, payment, order)
        elif payment_method.name == 'ZALOPAY':
            return request.process_zalopay_payment(request, payment, order)
        else:
            # Handle unsupported payment method
            payment.status = 'FAILED'
            payment.save()
            return render(request, 'payments/payment_failed.html', {
                'order': order,
                'error': 'Unsupported payment method'
            })

        # ========== COD PAYMENT ==========
        def process_cod_payment(request, payment, order):
            """
            Process Cash on Delivery payment
            """
            # For COD, we just mark the payment as pending
            payment.status = 'PENDING'
            payment.transaction_id = f"COD-{order.order_number}"
            payment.save()

            # Update order status - adjust to match your order status workflow
            order.status = 'PROCESSING'  # Make sure this status exists in your model
            order.save()

            return render(request, 'payments/payment_success.html', {
                'order': order,
                'payment': payment
            })

        # ========== PAYPAL PAYMENT ==========
        def process_paypal_payment(request, payment, order, paypalrestsdk=None):
            """
            Initialize PayPal payment process
            """
            # Configure PayPal SDK
            paypalrestsdk.configure({
                "mode": settings.PAYPAL_MODE,  # "sandbox" or "live"
                "client_id": settings.PAYPAL_CLIENT_ID,
                "client_secret": settings.PAYPAL_CLIENT_SECRET
            })

            # Create PayPal payment
            paypal_payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(f'/payment/paypal/execute/{payment.id}/'),
                    "cancel_url": request.build_absolute_uri(f'/payment/canceled/')
                },
                "transactions": [{
                    "amount": {
                        "total": str(order.total_amount),
                        "currency": "VND"  # Change according to your currency
                    },
                    "description": f"Payment for Order #{order.order_number}"
                }]
            })

            # Create PayPal payment
            if paypal_payment.create():
                # Payment created successfully
                payment.transaction_id = paypal_payment.id
                payment.payment_data = paypal_payment.to_dict()
                payment.save()

                # Redirect user to PayPal approval URL
                for link in paypal_payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)

            # Payment creation failed
            payment.status = 'FAILED'
            payment.save()
            return render(request, 'payments/payment_failed.html', {
                'order': order,
                'error': 'Failed to initialize PayPal payment'
            })

        @login_required
        def execute_paypal_payment(request, payment_id, paypalrestsdk=None):
            """
            Execute PayPal payment after user approval
            """
            payment = get_object_or_404(Payment, id=payment_id)
            order = payment.order

            payment_id = request.GET.get('paymentId')
            payer_id = request.GET.get('PayerID')

            paypalrestsdk.configure({
                "mode": settings.PAYPAL_MODE,
                "client_id": settings.PAYPAL_CLIENT_ID,
                "client_secret": settings.PAYPAL_CLIENT_SECRET
            })

            paypal_payment = paypalrestsdk.Payment.find(payment_id)

            if paypal_payment.execute({"payer_id": payer_id}):
                # Payment executed successfully
                payment.status = 'COMPLETED'
                payment.payment_data = paypal_payment.to_dict()
                payment.save()

                # Update order status
                order.status = 'PROCESSING'  # Adjust to match your order status
                order.save()

                return render(request, 'payments/payment_success.html', {
                    'order': order,
                    'payment': payment
                })
            else:
                # Payment execution failed
                payment.status = 'FAILED'
                payment.save()
                return render(request, 'payments/payment_failed.html', {
                    'order': order,
                    'error': 'PayPal payment execution failed'
                })

        # ========== STRIPE PAYMENT ==========
        def process_stripe_payment(request, payment, order, stripe=None):
            """
            Process payment using Stripe Checkout
            """
            # Set up Stripe API key
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Get user details from order for prefilling checkout
            customer_name = f"{order.user.first_name} {order.user.last_name}"
            customer_email = order.user.email

            # Create line items from order items
            line_items = []
            for item in order.orderitem_set.all():  # Adjust based on your model relationships
                line_items.append({
                    'price_data': {
                        'currency': 'vnd',  # Change according to your currency
                        'product_data': {
                            'name': item.product.name,  # Adjust based on your model fields
                            'description': item.product.description[:100] if hasattr(item.product,
                                                                                     'description') else '',
                        },
                        'unit_amount': int(item.price * 100),  # Amount in cents
                    },
                    'quantity': item.quantity,
                })

            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                customer_email=customer_email,
                mode='payment',
                success_url=request.build_absolute_uri(f'/payment/stripe/success/{payment.id}/'),
                cancel_url=request.build_absolute_uri('/payment/canceled/'),
            )

            # Store the Stripe session ID
            payment.transaction_id = session.id
            payment.payment_data = {
                'session_id': session.id,
                'session_url': session.url,
            }
            payment.save()

            # Redirect to Stripe Checkout
            return redirect(session.url)

        @login_required
        def stripe_success(request, payment_id):
            """
            Handle successful Stripe payment
            """
            payment = get_object_or_404(Payment, id=payment_id)
            order = payment.order

            # Update payment status
            payment.status = 'COMPLETED'
            payment.save()

            # Update order status
            order.status = 'PROCESSING'  # Adjust to match your order status
            order.save()

            return render(request, 'payments/payment_success.html', {
                'order': order,
                'payment': payment
            })

        @csrf_exempt
        def stripe_webhook(request, stripe=None):
            """
            Handle Stripe webhook events
            """
            payload = request.body
            sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
                )
            except ValueError:
                # Invalid payload
                return HttpResponse(status=400)
            except stripe.error.SignatureVerificationError:
                # Invalid signature
                return HttpResponse(status=400)

            # Handle the event
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']

                # Find the payment with this transaction ID
                try:
                    payment = Payment.objects.get(transaction_id=session.id)
                    payment.status = 'COMPLETED'
                    payment.save()

                    # Update order
                    order = payment.order
                    order.status = 'PROCESSING'  # Adjust to match your order status
                    order.save()
                except Payment.DoesNotExist:
                    # No matching payment found
                    pass

            return HttpResponse(status=200)

        # ========== MOMO PAYMENT ==========
        def process_momo_payment(request, payment, order):
            """
            Process payment using MoMo e-wallet
            """
            # MoMo API settings
            momo_endpoint = settings.MOMO_API_ENDPOINT
            partner_code = settings.MOMO_PARTNER_CODE
            access_key = settings.MOMO_ACCESS_KEY
            secret_key = settings.MOMO_SECRET_KEY

            # Generate unique request ID
            request_id = str(uuid.uuid4())
            order_id = f"MOMO-{order.order_number}"

            # Request data
            request_data = {
                'partnerCode': partner_code,
                'accessKey': access_key,
                'requestId': request_id,
                'amount': int(order.total_amount),
                'orderId': order_id,
                'orderInfo': f'Payment for Order #{order.order_number}',
                'returnUrl': request.build_absolute_uri(f'/payment/momo/return/{payment.id}/'),
                'notifyUrl': request.build_absolute_uri('/payment/momo/notify/'),
                'extraData': '',
                'requestType': 'captureMoMoWallet'
            }

            # Create signature
            raw_signature = f"accessKey={access_key}&amount={request_data['amount']}&extraData={request_data['extraData']}&orderId={order_id}&orderInfo={request_data['orderInfo']}&partnerCode={partner_code}&requestId={request_id}&returnUrl={request_data['returnUrl']}"
            signature = hmac.new(secret_key.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()
            request_data['signature'] = signature

            # Send request to MoMo
            response = requests.post(momo_endpoint, json=request_data)
            momo_response = response.json()

            if momo_response.get('errorCode') == 0:
                # Store transaction details
                payment.transaction_id = momo_response.get('orderId')
                payment.payment_data = momo_response
                payment.save()

                # Redirect to MoMo payment page
                return redirect(momo_response.get('payUrl'))
            else:
                # Payment initialization failed
                payment.status = 'FAILED'
                payment.payment_data = momo_response
                payment.save()
                return render(request, 'payments/payment_failed.html', {
                    'order': order,
                    'error': f"MoMo error: {momo_response.get('message')}"
                })

        @csrf_exempt
        def momo_notify(request):
            """
            MoMo payment notification webhook
            """
            if request.method == 'POST':
                data = json.loads(request.body)

                # Verify the transaction
                if data.get('resultCode') == 0:
                    try:
                        order_id = data.get('orderId')
                        payment = Payment.objects.get(transaction_id=order_id)
                        payment.status = 'COMPLETED'
                        payment.payment_data = data
                        payment.save()

                        # Update order
                        order = payment.order
                        order.status = 'PROCESSING'  # Adjust to match your order status
                        order.save()
                    except Payment.DoesNotExist:
                        pass

            return HttpResponse(status=200)

        @login_required
        def momo_return(request, payment_id):
            """
            Handle MoMo payment return page
            """
            payment = get_object_or_404(Payment, id=payment_id)
            order = payment.order

            # Get status from MoMo callback
            result_code = request.GET.get('resultCode')

            if result_code == '0':
                # Payment successful
                payment.status = 'COMPLETED'
                payment.payment_data = dict(request.GET.items())  # Store callback data
                payment.save()

                # Update order
                order.status = 'PROCESSING'  # Adjust to match your order status
                order.save()

                return render(request, 'payments/payment_success.html', {
                    'order': order,
                    'payment': payment
                })
            else:
                # Payment failed
                payment.status = 'FAILED'
                payment.payment_data = dict(request.GET.items())  # Store callback data
                payment.save()
                return render(request, 'payments/payment_failed.html', {
                    'order': order,
                    'error': f"MoMo payment failed: {request.GET.get('message')}"
                })

        # ========== ZALOPAY PAYMENT ==========
        def process_zalopay_payment(request, payment, order):
            """
            Process payment using ZaloPay
            """
            # ZaloPay API settings
            zalopay_endpoint = settings.ZALOPAY_CREATE_ORDER_URL
            app_id = settings.ZALOPAY_APP_ID
            key1 = settings.ZALOPAY_KEY1
            key2 = settings.ZALOPAY_KEY2

            # Generate app transaction ID
            app_trans_id = f"{int(time.time())}"

            # Prepare order data
            order_data = {
                "app_id": app_id,
                "app_trans_id": app_trans_id,
                "app_user": str(order.user.id),
                "app_time": int(time.time()),
                "amount": int(order.total_amount),
                "item": json.dumps([{"name": f"Order #{order.order_number}"}]),
                "description": f"Payment for Order #{order.order_number}",
                "embed_data": json.dumps({"payment_id": payment.id}),
                "bank_code": "zalopayapp",
                "callback_url": request.build_absolute_uri('/payment/zalopay/callback/')
            }

            # Generate MAC for authentication
            data_str = f"{app_id}|{app_trans_id}|{order_data['app_user']}|{order_data['amount']}|{order_data['app_time']}|{order_data['embed_data']}|{order_data['item']}"
            mac = hmac.new(key1.encode(), data_str.encode(), hashlib.sha256).hexdigest()
            order_data["mac"] = mac

            # Call ZaloPay API
            response = requests.post(zalopay_endpoint, json=order_data)
            zalopy_response = response.json()

            if zalopy_response.get('return_code') == 1:
                # Store transaction details
                payment.transaction_id = app_trans_id
                payment.payment_data = zalopy_response
                payment.save()

                # Redirect to ZaloPay payment page or show QR code
                return render(request, 'payments/zalopay_payment.html', {
                    'order': order,
                    'payment': payment,
                    'order_url': zalopy_response.get('order_url'),
                    'qr_code': zalopy_response.get('qr_code')
                })
            else:
                # Payment initialization failed
                payment.status = 'FAILED'
                payment.payment_data = zalopy_response
                payment.save()
                return render(request, 'payments/payment_failed.html', {
                    'order': order,
                    'error': f"ZaloPay error: {zalopy_response.get('return_message')}"
                })

        @csrf_exempt
        def zalopay_callback(request):
            """
            ZaloPay payment callback webhook
            """
            if request.method == 'POST':
                data = json.loads(request.body)

                # Verify callback data with ZaloPay
                app_id = settings.ZALOPAY_APP_ID
                key2 = settings.ZALOPAY_KEY2

                # Verify signature
                data_str = f"{data.get('app_id')}|{data.get('app_trans_id')}|{data.get('app_user')}|{data.get('amount')}|{data.get('app_time')}|{data.get('embed_data')}|{data.get('item')}"
                mac = hmac.new(key2.encode(), data_str.encode(), hashlib.sha256).hexdigest()

                if mac == data.get('mac') and data.get('status') == 1:
                    # Payment successful
                    embed_data = json.loads(data.get('embed_data'))
                    payment_id = embed_data.get('payment_id')

                    try:
                        payment = Payment.objects.get(id=payment_id)
                        payment.status = 'COMPLETED'
                        payment.payment_data = data
                        payment.save()

                        # Update order
                        order = payment.order
                        order.status = 'PROCESSING'  # Adjust to match your order status
                        order.save()

                        # Respond to ZaloPay
                        response_data = {
                            "return_code": 1,
                            "return_message": "success"
                        }
                        return JsonResponse(response_data)
                    except Payment.DoesNotExist:
                        pass

                # Respond with error
                response_data = {
                    "return_code": 0,
                    "return_message": "failed"
                }
                return JsonResponse(response_data)

            return HttpResponse(status=400)

        # Payment canceled view - generic for all payment methods
        def payment_canceled(request):
            """
            Generic payment canceled page
            """
            return render(request, 'payments/payment_canceled.html')






