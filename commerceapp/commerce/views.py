from gc import get_objects
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

from .models import Category, Product, Comment, User, Role, Shop, ShopProduct
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer, UserSerializer, ShopSerializer, ShopProductSerializer
from . import serializers, paginator
from . import permission

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






