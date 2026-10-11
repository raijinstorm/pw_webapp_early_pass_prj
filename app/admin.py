from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Client, Configuration
admin.site.register(User, UserAdmin)
admin.site.register(Product)
admin.site.register(Client)
admin.site.register(Configuration)

from .models import SchemaField
admin.site.register(SchemaField)

from .models import Membership
admin.site.register(Membership)
