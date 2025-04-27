from collections import Counter

from django.db.models import Count
from django.utils.html import mark_safe
from django.contrib import admin
from .models import Product, User, Role, Category, Shop, Order, OrderDetail, Payment, Comment, Like, ChatMessage, Conversation
from django.template.response import TemplateResponse
from django.urls import path
class MyProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'Product_status', 'category']
    search_fields = ['name', 'price']
    list_filter = ['id']
    list_editable = ['name']
    # fields = ['Mã sản phẩm', 'Tên sản phẩm', 'giá tiền', 'trạng thái', 'danh mục']

    def Product_status(self, obj):
        return obj.get_status_display()

    Product_status.short_description = 'Trạng thái sản phẩm'

    class Media:
        css = {
            'all' : ('/static/css/style.css',)
        }

class MyRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'role']
    search_fields = ['role']
    list_filter = ['id']
    list_editable = ['role']

    class Media:
        css = {
            'all' : ('/static/css/style.css',)
        }

class MyAdminSite(admin.AdminSite):
    site_header = 'E-Commerce-NM'

    def get_urls(self):
        return [path('product-stats', self.product_stats),] + super().get_urls()
    def product_stats(self, request):
        stats = Category.objects.annotate(c = Count('products')).values('id', 'name', 'c')
        return TemplateResponse(request, 'admin/stats.html', {
            'stats' : stats
        })
admin_site = MyAdminSite(name='eCommerce')

# Register your models here.
admin_site.register(Product, MyProductAdmin)
admin_site.register(User)
admin_site.register(Role, MyRoleAdmin)
admin_site.register(Category)
admin_site.register(Shop)
admin_site.register(Order)
admin_site.register(OrderDetail)
admin_site.register(Payment)
admin_site.register(Comment)
admin_site.register(Like)
admin_site.register(Conversation)
admin_site.register(ChatMessage)
