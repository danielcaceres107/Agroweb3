from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistroForm(UserCreationForm):
    username = forms.CharField(label="Nombre de usuario")
    password1 = forms.CharField(label="Contraseña")
    password2 = forms.CharField(label="Confirmación de contraseña")
    ROLE_CHOICES = (
        ('Vendedor', 'Vendedor'),
        ('Comprador', 'Comprador'),
        ('Superusuario', 'Superusuario'),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Rol")

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'role')
