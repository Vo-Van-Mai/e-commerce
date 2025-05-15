

import cloudinary
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from ckeditor.fields import RichTextField
from unicodedata import category
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class User(AbstractUser):
    phone = models.CharField(max_length=15, unique=True)
    avatar = CloudinaryField(
        'image',
        blank=True,
        null=True
    )

    class GenderUser(models.TextChoices):
        MALE = "Male", "Nam"
        FEMALE = "Female", "Nữ"
        OTHER = "Other", "Khác"

    gender = models.CharField(
        max_length=10,
        choices=GenderUser.choices,
        default=GenderUser.OTHER,
        null = True
    )

    is_verified_seller = models.BooleanField(default=False)

    class RoleType(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Nhân viên'
        SELLER = 'seller', 'Người bán'
        BUYER = 'buyer', 'Người mua'

    role = models.CharField(choices=RoleType.choices, default=RoleType.BUYER, max_length=20)

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id'] #sap xep giam theo id (cai nao moi thi len truoc nao cu thi o sau

class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(default="No description provided")

    def __str__(self):
        return self.name


class Product(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Tên sản phẩm")
    description = RichTextField()
    image = CloudinaryField('image', blank=True, null=True)
    category = models.ForeignKey(Category,on_delete=models.PROTECT, related_name='products')
    def __str__(self):
        return self.name


class Shop(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="shop")
    products = models.ManyToManyField(Product, related_name='shops', blank=True, through='ShopProduct')
    avatar = CloudinaryField('image', null=True)
    def __str__(self):
        return self.name


class ShopProduct(BaseModel):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Giá")
    quantity = models.IntegerField(default=0)
    class ProductStatus(models.TextChoices):
        AVAILABLE = "available", "Còn hàng"
        SOLD_OUT = "sold_out", "Hết hàng"
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,  # gan gia tri trong enum cho status
        default=ProductStatus.AVAILABLE  # gia tri mac dinh khi them san pham
    )

    class Meta:
        unique_together = ('shop', 'product')

    def __str__(self):
        return f"{self.shop.name} - {self.product.name if self.product else 'No Product'}"


class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=0)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderDetail(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    shop_product = models.ForeignKey(ShopProduct, on_delete=models.CASCADE, related_name='order_details')
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.shop_product.product.name} x{self.quantity} for Order #{self.order.id}"


class Payment(BaseModel):
    payment_method_choices = [
        ('cod', 'Cash On Delivery'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
        ('momo', 'MoMo'),
        ('zalopay', 'ZaloPay'),
    ]

    payment_status_choices = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.ForeignKey('order', on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=payment_method_choices)
    status = models.CharField(max_length=20, choices=payment_status_choices, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_details = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')

    def __str__(self):
        return f"{self.method} payment for order {self.order.id}"

class Meta:
    ordering = ['-created_date']


class Review(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class Comment(Review):
    content = models.TextField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.content

class Like(Review):
    star = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_product_like')
        ]
    def __str__(self):
        return str(self.star)

class Conversation(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='conversations')
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'shop'], name='unique_user_shop_conversation')
        ]

class ChatMessage(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_messages')
    sender_shop = models.ForeignKey(Shop, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_shop_messages')
    is_system = models.BooleanField(default=False)  # True nếu hệ thống gửi tự động
    message = models.TextField()

    def __str__(self):
        return f"{self.message[:30]}..."

class Cart(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    shop_product = models.ForeignKey(ShopProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'shop_product'], name='unique_cart_product')
        ]

