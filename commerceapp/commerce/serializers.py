from itertools import product

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Category, Product, Comment, User, Role, Shop, ShopProduct, Like

class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_date']


class ProductSerializer(ModelSerializer):
    #ghi de lai de can thiep du lieu dau ra
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = instance.image.url if instance.image else ''
        return data
    class Meta:
        model = Product
        fields = ['id', 'name', 'image' , 'category', 'created_by']


class CommentSerializer(ModelSerializer):
    def to_representation(self, comment):
        req = super().to_representation(comment)
        req['user'] = {
            'username': comment.user.username,
            'avatar': comment.user.avatar.url if comment.user.avatar else None
        }
        return req
    class Meta:
        model = Comment
        fields = ["content", "user", "parent", "created_date", "updated_date"]

class RoleSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name']


class UserSerializer(ModelSerializer):
    def create(self, validated_data):
        u = User(**validated_data)
        u.set_password(u.password)
        u.save()

        return u

    class Meta:
        role = RoleSerializer
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'gender' ,'phone', 'avatar']
        extra_kwargs ={
            'password' : {
                "write_only": True
            },
            'avatar': {
                       'error_messages': {
                           'required' : 'vui lòng upload avatar (ảnh đại diện) của bạn!!'
                       }
                   }
        }


class ShopSerializer(ModelSerializer):

    class Meta:
        model = Shop
        fields = ['id', 'name', 'user', 'avatar']
        extra_kwargs={
            'user': {'read_only': True},
            'avatar': {
                'error_messages': {
                    'required': 'vui lòng upload avatar (ảnh đại diện) của shop!!'
                }
            }
        }



class ShopProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    class Meta:
        model = ShopProduct
        fields = ['id', 'shop', 'product', 'price', 'quantity', 'status']
        extra_kwargs = {
            'shop': {'read_only': True}
        }
    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        product_data = validated_data.pop('product')
        product = Product.objects.create(created_by=user,**product_data)
        shopproduct = ShopProduct.objects.create(product=product, **validated_data)
        return shopproduct

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['id', 'star']



