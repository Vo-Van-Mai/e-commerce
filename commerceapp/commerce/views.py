from django.http import HttpResponse
from rest_framework import viewsets, permissions
from .models import Category
from . import serializers

def index(request):
    return HttpResponse("E-commerce")

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(active=True)
    serializer_class = serializers.CategprySerializer