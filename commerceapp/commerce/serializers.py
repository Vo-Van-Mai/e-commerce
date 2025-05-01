from rest_framework.serializers import ModelSerializer
from .models import Category, Product, Comment, User, Role

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
        fields = ['id', 'name', 'price', 'quantity', 'status', 'image' , 'category_id']

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
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'gender' ,'phone', 'avatar', 'role']
        extra_kwargs ={
            'password' : {
                "write_only": True
            }
        }
