from django.urls import path, include
from . import views, admin
from . import webhooks
from rest_framework import routers

r = routers.DefaultRouter()
r.register('categories', views.CategoryViewSet)
r.register('products', views.ProductViewSet, basename='products')
r.register('users', views.UserViewSet, basename='users')
r.register('shops', views.ShopViewSet, basename='shops')
r.register('shop-products', views.ShopProductViewSet, basename='shopproduct')
r.register('payments', views.PaymentViewSet, basename='payments')
r.register('comments', views.CommentViewSet, basename='comments')
r.register('likes', views.likeViewSet, basename='likes')
urlpatterns = [
    path('', include(r.urls))
]

# URL patterns for payment API
urlpatterns = [
    path('', include(r.urls)),
    path('webhooks/stripe/', webhooks.stripe_webhook, name='stripe-webhook'),
    path('webhooks/momo/', webhooks.momo_webhook, name='momo-webhook'),
    path('webhooks/zalopay/', webhooks.zalopay_webhook, name='zalopay-webhook'),
]
