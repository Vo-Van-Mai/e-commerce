from django.urls import path, include
from . import views, admin
from rest_framework import routers

r = routers.DefaultRouter()
r.register('categories', views.CategoryViewSet)
r.register('products', views.ProductViewSet, basename='products')
r.register('users', views.UserViewSet, basename='users')
r.register('shops', views.ShopViewSet, basename='shops')
r.register('shop-products', views.ShopProductViewSet, basename='shopproduct')

urlpatterns = [
    path('', include(r.urls))
]

# Payment URLs
urlpatterns += [
    path('payment/select/<int:order_id>/', views.PaymentViewSet.payment_selection, name='payment_selection'),
    path('payment/process/<int:order_id>/', views.PaymentViewSet.process_payment, name='process_payment'),
    path('payment/canceled/', views.PaymentViewSet.payment_canceled, name='payment_canceled'),

    # PayPal URLs
    path('payment/paypal/execute/<int:payment_id>/', views.PaymentViewSet.execute_paypal_payment, name='execute_paypal_payment'),

    # Stripe URLs
    path('payment/stripe/success/<int:payment_id>/', views.PaymentViewSet.stripe_success, name='stripe_success'),
    path('payment/stripe/webhook/', views.PaymentViewSet.stripe_webhook, name='stripe_webhook'),

    # MoMo URLs
    path('payment/momo/return/<int:payment_id>/', views.PaymentViewSet.momo_return, name='momo_return'),
    path('payment/momo/notify/', views.PaymentViewSet.momo_notify, name='momo_notify'),

    # ZaloPay URLs
    path('payment/zalopay/callback/', views.PaymentViewSet.zalopay_callback, name='zalopay_callback'),
]
