import base64
from abc import ABC, abstractmethod
import hashlib
import json
import uuid
import stripe
from datetime import time

from django.shortcuts import get_object_or_404
from django.utils import timezone
from gc import get_objects
from http.client import responses
from pickle import FALSE
from urllib.request import Request
# from tarfile import TruncatedHeaderError
from xmlrpc.client import ResponseError

from django.http import HttpResponse
from rest_framework import viewsets, permissions, generics, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from rest_framework.serializers import ValidationError
from unicodedata import category

from .models import Category, Product, Comment, User, Shop, ShopProduct, Payment, Like
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer, UserSerializer, ShopSerializer, ShopProductSerializer, PaymentSerializer, PaymentInitSerializer, PaymentVerifySerializer, LikeSerializer
from .services import PaymentFactory
from . import serializers, paginator
from . import permission
from django.conf import settings


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
    queryset = Product.objects.prefetch_related('shopproduct_set').filter(active=True)
    serializer_class = serializers.ProductSerializer
    pagination_class = paginator.ItemPaginator

    def get_permissions(self):
        if self.action in ['get_commments', 'get_rating'] and self.request.method.__eq__('POST'):
            return [permissions.IsAuthenticated()]
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permission.IsSeller()]
        return [AllowAny()]

    def get_queryset(self):
        query = self.queryset
        #tim san pham theo ten
        name = self.request.query_params.get('name')
        if name:
            query = query.filter(name__icontains=name)

        #tim san pham theo danh muc
        cate_id = self.request.query_params.get('cate_id')
        if cate_id:
            query = query.filter(category__id = cate_id)

        # Lọc theo khoảng giá từ bảng trung gian ShopProduct
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            query = query.filter(shopproduct__price__gte=min_price)
        if max_price:
            query = query.filter(shopproduct__price__lte=max_price)

        #Lọc theo shop
        shop = self.request.query_params.get('shop')
        if shop:
            query = query.filter(shop__id=shop)

        #sắp xếp theo giá
        ordering = self.request.query_params.get('ordering')
        if ordering == 'price':
            query = query.order_by('shopproduct__price')
        elif ordering == '-price':
            query = query.order_by('-shopproduct__price')

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

    @action(methods=['get','post'], detail=True, url_path="rating")
    def get_rating(self, request, pk):
        product = self.get_object()

        if request.method.__eq__('POST'):
            star = request.data.get('star')
            if not star:
                return Response({'error': 'Thiếu dữ liệu đánh giá (star)'}, status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra đánh giá đã tồn tại chưa
            like, created = Like.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={'star': star}
            )

            if not created:
                # Nếu đã tồn tại thì cập nhật số sao
                like.star = star
                like.save()
                return Response(LikeSerializer(like).data, status=status.HTTP_200_OK)

            return Response(LikeSerializer(like).data, status=status.HTTP_201_CREATED)

        else:
            star = product.like_set.select_related('user').filter(active=True).order_by('-id')
            p = paginator.ProductPaginator()
            page = p.paginate_queryset(star, self.request)
            if page:
                s = LikeSerializer(page, many=True)
                return p.get_paginated_response(s.data)
            else:
                return Response(LikeSerializer(star, many=True).data, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [parsers.MultiPartParser]


    def register_user(self, request, role_name, is_staff=False):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.role = role_name
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
        role = 'seller'
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
    """ViewSet for viewing and editing Payment instances"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all payments
        for the currently authenticated user.
        """
        user = self.request.user

        # If staff, return all payments
        if user.is_staff:
            return Payment.objects.all()

        # Otherwise, return only user's payments
        return Payment.objects.filter(order__user=user)

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """
        Initialize a payment
        """
        serializer = PaymentInitSerializer(data=request.data)

        if serializer.is_valid():
            order_id = serializer.validated_data['order_id']
            method = serializer.validated_data['method']
            return_url = serializer.validated_data.get('return_url')

            # Get the order
            try:
                from models import Order
                order = Order.objects.get(id=order_id, user=request.user)
            except Order.DoesNotExist:
                return Response(
                    {'error': 'Order not found or does not belong to user'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Create payment
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,  # Assuming Order model has total_amount field
                method=method
            )

            # Process payment
            processor = PaymentFactory.get_processor(method)
            result = processor.process_payment(payment, return_url)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': result.get('message', 'Payment initialization failed')
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verify a payment
        """
        serializer = PaymentVerifySerializer(data=request.data)

        if serializer.is_valid():
            payment_id = serializer.validated_data['payment_id']
            transaction_id = serializer.validated_data.get('transaction_id')
            payment_data = serializer.validated_data.get('payment_data')

            # Get the payment
            payment = get_object_or_404(Payment, id=payment_id)

            # Check if the payment belongs to the user if not staff
            if not request.user.is_staff and payment.order.user != request.user:
                return Response(
                    {'error': 'Payment does not belong to user'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Verify payment
            processor = PaymentFactory.get_processor(payment.method)
            result = processor.verify_payment(payment, transaction_id, payment_data)

            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': result.get('message', 'Payment verification failed')
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def methods(self, request):
        """
        Get available payment methods
        """
        return Response({
            'methods': [{'value': k, 'label': v} for k, v in Payment.payment_method_choices]
        })

class CommentViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = CommentSerializer
    permission_classes = [permission.IsCommentOwner]


class likeViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Like.objects.filter(active=True)
    serializer_class = LikeSerializer
    permission_classes = [permission.IsRatingOwner]


