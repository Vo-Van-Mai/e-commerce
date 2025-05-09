from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Category, Product, Comment, User, Role, Shop, ShopProduct

class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_date']


class ShopProductSerializer(ModelSerializer):

    class ShopProductSerializer(serializers.ModelSerializer):
        product_name = serializers.CharField(write_only=True)
        category_id = serializers.IntegerField(write_only=True)

        class Meta:
            model = ShopProduct
            fields = ['id', 'shop', 'product_name', 'category_id', 'price', 'quantity', 'status']
            extra_kwargs = {
                'status': {'required': False}
            }

        def create(self, validated_data):
            product_name = validated_data.pop('product_name')
            category_id = validated_data.pop('category_id')

            # Lấy category từ hệ thống
            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError({'category_id': 'Không tồn tại danh mục này'})

            # Lấy user đang login
            user = self.context['request'].user

            # Tạo sản phẩm mới
            product = Product.objects.create(
                name=product_name,
                description="Tạo tự động từ ShopProduct",
                category=category,
                created_by=user
            )

            validated_data['product'] = product
            return super().create(validated_data)


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
            'avatar': comment.user.avatar
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


