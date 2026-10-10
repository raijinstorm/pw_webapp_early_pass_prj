from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Client, Configuration
admin.site.register(User, UserAdmin)
admin.site.register(Product)
admin.site.register(Client)
admin.site.register(Configuration)
