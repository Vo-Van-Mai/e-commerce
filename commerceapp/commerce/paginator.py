from rest_framework.pagination import PageNumberPagination

class ItemPaginator(PageNumberPagination):
    page_size = 5


class ProductPaginator(PageNumberPagination):
    page_size = 2