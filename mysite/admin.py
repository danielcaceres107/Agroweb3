from django.contrib import admin
from .models import DimVendedores, DimProducts, DimClientes

admin.site.register(DimVendedores)
admin.site.register(DimProducts)
admin.site.register(DimClientes)