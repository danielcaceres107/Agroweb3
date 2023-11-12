from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Vendedores, Products, Clientes


class RegistroVendedorForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de usuario")
    nombreVendedor = forms.CharField(label="Nombre completo del vendedor")
    cedula = forms.CharField(label="Cedula")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmación de contraseña")
    nombreTienda = forms.CharField(label="Nombre de la tienda")
    telefono = forms.CharField(label="Telefono")
    documentoMercantil = forms.FileField(label="Adjuntar Registro Mercantil", required=False)
    latitude = forms.CharField(label="Latitud")
    longitude = forms.CharField(label="Longitud")
    horario = forms.CharField(label="Horario de la tienda")
    productos = forms.ModelMultipleChoiceField(queryset=Products.objects.all(), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = User
        fields = ('username', 'nombreVendedor', 'cedula', 'password1', 'password2', 'nombreTienda', 'telefono', 'documentoMercantil','latitude', 'longitude', 'horario', 'productos')

class RegistroClientesForm(forms.ModelForm):
    nombreCliente = forms.CharField(label="Nombre Completo")
    username = forms.CharField(label="Nombre de usuario")
    correo = forms.CharField(label="Correo")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmación de contraseña")

    class Meta:
        model = User
        fields = ('username', 'nombreCliente', 'correo', 'password1', 'password2')

class EditarPerfilForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de usuario")
    nombreTienda = forms.CharField(label="Nombre de la tienda")
    telefono = forms.CharField(label="Teléfono")
    latitude = forms.CharField(label="Latitud")
    longitude = forms.CharField(label="Longitud")
    horario = forms.CharField(label="Horario de la tienda")
    productos = forms.ModelMultipleChoiceField(queryset=Products.objects.all(), widget=forms.SelectMultiple)

    class Meta:
        model = User
        fields = ('username', 'nombreTienda', 'telefono', 'latitude', 'longitude', 'horario', 'productos')


class ProductoForm(forms.ModelForm):
    nombreProd = forms.CharField(label="Nombre del producto")
    precioProd = forms.CharField(label="Precio del producto")
    descripcionProd = forms.CharField(label="Descripcion del producto")
    imagenProd = forms.ImageField(label="Imagen del producto")
    class Meta:
        model = Products
        fields = ['nombreProd', 'precioProd', 'descripcionProd', 'imagenProd']
