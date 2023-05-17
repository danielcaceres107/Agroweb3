from django.db import models
from django.contrib.auth.models import User
import hashlib

#create your models here
class DimProducts(models.Model):
    nombreProd = models.CharField(max_length=200)
    precioProd = models.DecimalField(max_digits=10, decimal_places=0)
    descripcionProd = models.TextField(max_length=500)
    imagenProd = models.ImageField(upload_to='img/', null=True, blank=True)
    # Otros campos que necesites

    def __str__(self):
        return self.nombreProd
class DimVendedores(models.Model):
    nombreVendedor = models.CharField(max_length=200, unique=True)
    nombreTienda = models.CharField(max_length=200,blank=True, null=True)
    cedula = models.CharField(max_length=20)
    telefono = models.CharField(max_length=200,blank=True, null=True)
    latitude = models.CharField(max_length=200,blank=True, null=True)
    longitude = models.CharField(max_length=200,blank=True, null=True)
    horario = models.CharField(max_length=200,blank=True, null=True)
    productos = models.ManyToManyField(DimProducts, related_name='productos_venta')

    def set_password(self, password):
        """Convierte el password a varbinary(max)"""
        self.password = hashlib.sha256(password.encode('utf-8')).digest()

    def __str__(self):
        return self.nombreVendedor
class DimClientes(models.Model):
    nombreCliente = models.CharField(max_length=200, unique=True)
    usuarioCliente = models.CharField(max_length=200, unique=True)
    correo = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nombreCliente