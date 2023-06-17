from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import hashlib


#create your models here
class Products(models.Model):
    nombreProd = models.CharField(max_length=200)
    precioProd = models.DecimalField(max_digits=10, decimal_places=0)
    descripcionProd = models.TextField(max_length=500)
    imagenProd = models.ImageField(upload_to='img/', null=True, blank=True)
    # Otros campos que necesites

    def __str__(self):
        return self.nombreProd
class Vendedores(models.Model):
    nombreVendedor = models.CharField(max_length=200, unique=True)
    usuarioVendedor = models.CharField(max_length=200, unique=True)
    nombreTienda = models.CharField(max_length=200,blank=True, null=True)
    cedula = models.CharField(max_length=20)
    telefono = models.CharField(max_length=200,blank=True, null=True)
    documentoMercantil = models.FileField(upload_to='pdfs/', blank=True, null=True)
    latitude = models.CharField(max_length=200,blank=True, null=True)
    longitude = models.CharField(max_length=200,blank=True, null=True)
    horario = models.CharField(max_length=200,blank=True, null=True)
    productos = models.ManyToManyField(Products, related_name='productos_venta')


    def set_password(self, password):
        """Convierte el password a varbinary(max)"""
        self.password = hashlib.sha256(password.encode('utf-8')).digest()

    def __str__(self):
        return self.nombreVendedor
    
    @receiver(pre_delete, sender=User)
    def delete_vendedor(sender, instance, **kwargs):
        # Eliminar la instancia de vendedor correspondiente al usuario que se está eliminando
        vendedor = Vendedores.objects.get(nombreVendedor=instance.username)
        vendedor.delete()
        
class Clientes(models.Model):
    nombreCliente = models.CharField(max_length=200, unique=True)
    usuarioCliente = models.CharField(max_length=200, unique=True)
    correo = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nombreCliente
    
@receiver(pre_delete, sender=User)
def delete_cliente(sender, instance, **kwargs):
    # Eliminar la instancia de cliente correspondiente al usuario que se está eliminando
    cliente = Clientes.objects.get(nombreCliente=instance.username)
    cliente.delete()