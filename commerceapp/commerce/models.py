from datetime import timezone
from tkinter.constants import CASCADE
from venv import create

import cloudinary
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from ckeditor.fields import RichTextField
from unicodedata import category


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

    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True)

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id'] #sap xep giam theo id (cai nao moi thi len truoc nao cu thi o sau

class Role(BaseModel):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name



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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products', null=True)
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
        return self.user

class OrderDetail(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_details')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=0)

    def __str__(self):
        return self.order

class Payment(BaseModel):
    class Payment(models.Model):
        PAYMENT_METHOD_CHOICES = [
            ('COD', 'Cash On Delivery'),
            ('PAYPAL', 'PayPal'),
            ('STRIPE', 'Stripe'),
            ('MOMO', 'MoMo'),
            ('ZALOPAY', 'ZaloPay'),
        ]

        STATUS_CHOICES = [
            ('PENDING', 'Pending'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('REFUNDED', 'Refunded'),
        ]

        order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
        amount = models.DecimalField(max_digits=10, decimal_places=2)
        payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
        status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
        transaction_id = models.CharField(max_length=255, blank=True, null=True)
        payment_date = models.DateTimeField(blank=True, null=True)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        # Additional fields for payment gateway specific data
        gateway_response = models.JSONField(blank=True, null=True)  # Stores any response from payment gateway

        def __str__(self):
            return f"Payment #{self.id} - {self.get_status_display()} via {self.get_payment_method_display()}"

        def mark_as_completed(self):
            """Mark payment as completed and update related order"""
            self.status = 'COMPLETED'
            self.payment_date = timezone.now()
            self.save()

            # Update order status to processing
            order = self.order
            order.status = 'PROCESSING'
            order.save()

        def mark_as_failed(self):
            """Mark payment as failed"""
            self.status = 'FAILED'
            self.save()

    # class PaymentMethod(models.IntegerChoices):
    #     Cash = 1, "Thanh toán tiền mặt"
    #     Online = 2, "Thanh toán online"
    #
    #     payment_method_choices = [
    #         ('COD', 'Cash On Delivery'),
    #         ('PAYPAL', 'PayPal'),
    #         ('STRIPE', 'Stripe'),
    #         ('MOMO', 'MoMo'),
    #         ('ZALOPAY', 'ZaloPay'),
    #     ]
    #     name = models.CharField(max_length=20, choices=payment_method_choices)
    #     description = models.TextField(blank=True, null=True)
    #     is_active = models.BooleanField(default=True)
    #     icon = models.ImageField(upload_to='payment_icons/', blank=True, null=True)
    #
    #     def __str__(self):
    #         return self.get_name_display()
    #
    # total_amount = models.DecimalField(max_digits=10, decimal_places=0)
    #
    # class PaymentStatus(models.TextChoices):
    #     status_choices = [
    #         ('pending', 'Chờ thanh toán'),
    #         ('completed', 'Thanh toán thành công'),
    #         ('failed', 'Thanh toán thất bại'),
    #         ('refunded', 'Hoàn tiền'),
    #     ]
    #
    # order = models.ForeignKey('commerce_order.Order', on_delete=models.CASCADE,
    #                           related_name='payments')  # Match your actual app and model name
    # amount = models.DecimalField(max_digits=10, decimal_places=2)
    # payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    # status = models.CharField(max_length=10, choices=status_choices, default='PENDING')
    # transaction_id = models.CharField(max_length=255, blank=True, null=True)
    # payment_data = models.JSONField(blank=True, null=True)  # Store response data from payment gateways
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    #
    # order = models.OneToOneField(Order, on_delete=models.CASCADE, primary_key=True)
    # payment_method= models.CharField(
    #     max_length=15,
    #     choices=PaymentMethod.choices,
    #     default=PaymentMethod.Cash
    # )
    # payment_status = models.CharField(
    #     max_length=15,
    #     choices=PaymentStatus.choices,
    #     default=PaymentStatus.PENDING
    # )
    #
    # def __str__(self):
    #     return f"Payment #{self.id} - {self.get_status_display()}"

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

