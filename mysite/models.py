from django.db import models

#create your models here
class DimVendedores(models.Model):
    nombreVendedor = models.CharField(max_length=200, unique=True)
    nombreTienda = models.CharField(max_length=200,blank=True, null=True)
    password = models.CharField(max_length=200,blank=True, null=True)
    telefono = models.CharField(max_length=200,blank=True, null=True)
    latitude = models.CharField(max_length=200,blank=True, null=True)
    longitude = models.CharField(max_length=200,blank=True, null=True)
    correo = models.CharField(max_length=200,blank=True, null=True)


    def __str__(self):
        return self.nombreVendedor
