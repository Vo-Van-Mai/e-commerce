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
    class ProductStatus(models.TextChoices):
        AVAILABLE = "available", "Còn hàng"
        SOLD_OUT = "sold_out", "Hết hàng"
    name = models.CharField(max_length=100, verbose_name="Tên sản phẩm")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Giá")
    description = RichTextField()
    image = CloudinaryField('image', blank=True, null=True)
    quantity = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices = ProductStatus.choices, # gan gia tri trong enum cho status
        default= ProductStatus.AVAILABLE # gia tri mac dinh khi them san pham
    )
    category = models.ForeignKey(Category,on_delete=models.PROTECT, related_name='products')

    def __str__(self):
        return self.name

class Shop(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shop")
    products = models.ManyToManyField(Product, related_name='shops')

    def __str__(self):
        return self.name

class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)


class OrderDetail(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_details')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(BaseModel):
    class PaymentMethod(models.IntegerChoices):
        Cash = 1, "Thanh toán tiền mặt"
        Online = 2, "Thanh toán online"

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Đang chờ"
        COMPLETED = "completed", "Đã thanh toán"
        FAILED = "failed", "Thanh toán thất bại"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, primary_key=True)
    payment_method= models.CharField(
        max_length=15,
        choices=PaymentMethod.choices,
        default=PaymentMethod.Cash
    )
    payment_status = models.CharField(
        max_length=15,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
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

