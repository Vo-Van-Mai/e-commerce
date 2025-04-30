from rest_framework.permissions import BasePermission

class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role.name == "seller")

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role.name == "buyer")

class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role.name == "staff")

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (request.user.is_authenticated and request.user.role.name == "admin")