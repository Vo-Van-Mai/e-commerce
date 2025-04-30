from rest_framework.serializers import ModelSerializer
from .models import Category, Product, Comment

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


