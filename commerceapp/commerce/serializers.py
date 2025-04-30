from rest_framework.serializers import ModelSerializer
from .models import Category, Product

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