from gc import get_objects
from pickle import FALSE
# from tarfile import TruncatedHeaderError
from xmlrpc.client import ResponseError

from django.http import HttpResponse
from rest_framework import viewsets, permissions, generics, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import Category, Product, Comment, User, Role
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer, UserSerializer
from . import serializers, paginator
from . import permission

def index(request):
    return HttpResponse("E-commerce")

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(active=True)
    serializer_class = serializers.CategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "destroy", "update", "partial_update"]:
            return permissions.IsAuthenticated
        return permissions.AllowAny

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
        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)
            
        cate_id = self.request.query_params.get('cate_ID')
        if cate_id:
            query = query.filter(category_id = cate_id)
        return query

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

    @action(methods=['get'], url_path='current-user', detail=False, permission_classes=[permissions.IsAuthenticated])
    def get_current_user(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)