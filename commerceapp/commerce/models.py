from tkinter.constants import CASCADE
from tokenize import blank_re

import cloudinary
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True)
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
        blank=True,
        null = True
    )

    role = models.ManyToManyField('Role')

class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id'] #sap xep giam theo id (cai nao moi thi len truoc nao cu thi o sau

class Role(BaseModel):
    role = models.CharField(max_length=50)

    def __str__(self):
        return self.role



class Category(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name


class Product(BaseModel):
    class ProductStatus(models.TextChoices):
        pass
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = CloudinaryField('image', blank=True, null=True)

    def __str__(self):
        return self.name

class Shop(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ManyToManyField(User)
    products = models.ManyToManyField(Product)

    def __str__(self):
        return self.name

class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.ManyToManyField(Product)

