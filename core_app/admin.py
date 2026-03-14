from django.contrib import admin

# Register your models here.
from .models import *
from django.apps import apps

from django.contrib import admin
from .models import Seller, User

class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'role', 'phone')
    search_fields = ('id', 'username', 'role', 'phone')
    list_filter = ('role',)


class SellerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "seller_type")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role__in=["vendor", "farmer"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Seller, SellerAdmin)
admin.site.register(User, UserAdmin)

models = apps.get_app_config('core_app').get_models()

for model in models:
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass
