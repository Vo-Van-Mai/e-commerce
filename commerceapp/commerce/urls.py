from django.urls import path, include
from . import  views
from rest_framework import routers

r = routers.DefaultRouter()
r.register('categories', views.CategoryViewSet)
r.register('products', views.ProductViewSet, basename='products')
r.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('', include(r.urls))
]