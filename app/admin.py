"""Django admin for reference data: users, products, clients and memberships.

Configurations and versions are read-only here: they change only through the app, so every change
goes through the database triggers (validation + versioning). Rows with history are never deleted:
users are deactivated instead, products and clients stay.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Client, Configuration, ConfigVersion, Membership, Product, User


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1


class NoDeleteMixin:
    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyMixin(NoDeleteMixin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(User)
class ConfigHubUserAdmin(NoDeleteMixin, UserAdmin):
    inlines = [MembershipInline]
    list_display = ["username", "email", "first_name", "last_name", "is_superuser", "is_active"]


@admin.register(Product)
class ProductAdmin(NoDeleteMixin, admin.ModelAdmin):
    list_display = ["name", "code", "created_at"]
    prepopulated_fields = {"code": ["name"]}
    inlines = [MembershipInline]


@admin.register(Client)
class ClientAdmin(NoDeleteMixin, admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Configuration)
class ConfigurationAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ["product", "client", "status", "version", "updated_at", "updated_by"]
    list_filter = ["product", "status"]


@admin.register(ConfigVersion)
class ConfigVersionAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ["configuration", "number", "author", "created_at", "comment"]
    list_filter = ["configuration__product"]
