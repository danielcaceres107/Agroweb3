from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import DimVendedores, DimProducts


class RegistroVendedorForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de usuario")
    password1 = forms.CharField(label="Contraseña")
    password2 = forms.CharField(label="Confirmación de contraseña")
    nombreTienda = forms.CharField(label="Nombre de la tienda")
    telefono = forms.CharField(label="Telefono")
    latitude = forms.CharField(label="Latitud")
    longitude = forms.CharField(label="Longitud")
    horario = forms.CharField(label="Horario de la tienda")
    productos = forms.ModelMultipleChoiceField(queryset=DimProducts.objects.all(), widget=forms.SelectMultiple)

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'nombreTienda', 'telefono', 'latitude', 'longitude', 'horario', 'productos')
