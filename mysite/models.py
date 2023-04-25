from django.db import models
from django.contrib.auth.models import User
import hashlib

#create your models here
class DimVendedores(models.Model):
    nombreVendedor = models.CharField(max_length=200, unique=True)
    nombreTienda = models.CharField(max_length=200,blank=True, null=True)
    password = models.BinaryField()
    telefono = models.CharField(max_length=200,blank=True, null=True)
    latitude = models.CharField(max_length=200,blank=True, null=True)
    longitude = models.CharField(max_length=200,blank=True, null=True)
    horario = models.CharField(max_length=200,blank=True, null=True)

    def set_password(self, password):
        """Convierte el password a varbinary(max)"""
        self.password = hashlib.sha256(password.encode('utf-8')).digest()

    def __str__(self):
        return self.nombreVendedor
