from gc import get_objects
from pickle import FALSE
# from tarfile import TruncatedHeaderError
from xmlrpc.client import ResponseError

from django.http import HttpResponse
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Category, Product, Comment
from .serializers import CategorySerializer, ProductSerializer, CommentSerializer
from . import serializers, paginator
from . import permissions

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
        if self.action in ["create", "update", "partial_update, destroy"]:
            return [permissions.IsSeller()]
        else :
            return [AllowAny()]

    def get_queryset(self):
        query = self.queryset
        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)
            
        cateid = self.request.query_params.get('cateID')
        if cateid:
            query = query.filter(category_id = cateid)
        return query

    @action(methods=['get'], url_path="comment", detail=True)
    def get_comments(self, request, pk):
        comments = self.get_object().comment_set.select_related('user').filter(active=True).order_by('-id')
        p = paginator.ProductPaginator()
        page = p.paginate_queryset(comments, self.request)
        if page:
            c = CommentSerializer(page, many=True)
            return p.get_paginated_response(c.data)
        else:
            return Response(CommentSerializer(comments, many = True).data, status=status.HTTP_201_CREATED)