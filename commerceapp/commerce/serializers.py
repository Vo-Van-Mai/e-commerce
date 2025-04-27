from rest_framework.serializers import ModelSerializer
from .models import Category

class CategprySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_date']