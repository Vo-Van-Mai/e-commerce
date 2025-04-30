from gc import get_objects
from xmlrpc.client import ResponseError

from django.http import HttpResponse
from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from . import serializers, paginator

def index(request):
    return HttpResponse("E-commerce")

class CategoryViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Category.objects.filter(active=True)
    serializer_class = serializers.CategorySerializer

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

class ProductViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Product.objects.filter(active=True)
    serializer_class = serializers.ProductSerializer
    pagination_class = paginator.ItemPaginator

    def get_queryset(self):
        query = self.queryset
        q = self.request.query_params.get('q')
        if q:
            query = query.filter(name__icontains=q)
            
        cateid = self.request.query_params.get('cateID')
        if cateid:
            query = query.filter(category_id = cateid)
        return query