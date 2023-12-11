from django.contrib import admin
from .models import Vendedores, Products, Clientes

admin.site.register(Vendedores)
admin.site.register(Products)
admin.site.register(Clientes)