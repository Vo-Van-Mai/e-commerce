from rest_framework.permissions import BasePermission
from rest_framework import permissions

class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and  # Kiểm tra sự tồn tại của role
            request.user.role.name == "seller" and
            request.user.is_verified_seller == True
        )

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and  # Kiểm tra sự tồn tại của role
            request.user.role.name == "buyer"
        )

class IsStaff(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and  # Kiểm tra sự tồn tại của role
            request.user.role.name == "staff"
        )

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role and  # Kiểm tra sự tồn tại của role
            request.user.role.name == "admin"
        )


class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser


class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role and ( request.user.role.name=="admin" or request.user.role.name=="staff")


class IsAdminOrSeller(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role and ( request.user.role.name=="admin" or request.user.role.name=="seller")

class IsCommentOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, comment):
        return super().has_permission(request, view) and request.user == comment.user

class IsRatingOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, like):
        return super().has_permission(request, view) and request.user == like.user