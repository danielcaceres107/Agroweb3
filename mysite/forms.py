from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import DimVendedores, DimProducts, DimClientes


class RegistroVendedorForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de usuario")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmación de contraseña")
    nombreTienda = forms.CharField(label="Nombre de la tienda")
    telefono = forms.CharField(label="Telefono")
    latitude = forms.CharField(label="Latitud")
    longitude = forms.CharField(label="Longitud")
    horario = forms.CharField(label="Horario de la tienda")
    productos = forms.ModelMultipleChoiceField(queryset=DimProducts.objects.all(), widget=forms.SelectMultiple)

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'nombreTienda', 'telefono', 'latitude', 'longitude', 'horario', 'productos')

class RegistroClientesForm(forms.ModelForm):
    nombreCliente = forms.CharField(label="Nombre del cliente")
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
    productos = forms.ModelMultipleChoiceField(queryset=DimProducts.objects.all(), widget=forms.SelectMultiple)

    class Meta:
        model = User
        fields = ('username', 'nombreTienda', 'telefono', 'latitude', 'longitude', 'horario', 'productos')
