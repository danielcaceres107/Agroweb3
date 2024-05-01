from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from .models import Vendedores, Products, Clientes


class RegistroVendedorForm(forms.ModelForm):
    username = forms.CharField(label="Nombre de usuario")
    nombreVendedor = forms.CharField(label="Nombre completo del vendedor")
    cedula = forms.CharField(label="Cedula")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmación de contraseña")
    nombreTienda = forms.CharField(label="Nombre de la tienda")
    correo = forms.EmailField(validators=[EmailValidator(message='')])
    telefono = forms.CharField(label="Telefono")
    documentoMercantil = forms.FileField(label="Adjuntar Registro Mercantil", required=False)
    latitude = forms.CharField(label="Latitud")
    longitude = forms.CharField(label="Longitud")
    horario = forms.CharField(label="Horario de la tienda")
    productos = forms.ModelMultipleChoiceField(queryset=Products.objects.all(), widget=forms.CheckboxSelectMultiple)
    imagen_qr = forms.ImageField(label="QR_Nequi", required=False)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 != password2:
            raise forms.ValidationError(
                "Las contraseñas no coinciden"
            )
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está en uso.")
        return username
    
    def clean_cedula(self):
        cedula = self.cleaned_data['cedula']
        if not cedula.isdigit():
            raise forms.ValidationError('Ingresa solo numeros en el campo de cedula')
        return cedula
    
    def clean_correo(self):
        correo = self.cleaned_data['correo']
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return correo
    
    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.isdigit() or len(telefono) != 10:
            raise forms.ValidationError('Ingresa un numero de telefono valido (ej: 3154043021)')
        return telefono
    
    def clean_documentoMercantil(self):
        documentoMercantil = self.cleaned_data.get('documentoMercantil')
        if documentoMercantil:
            try:
                if not documentoMercantil.name.endswith('.pdf'):
                    raise forms.ValidationError('El documento mercantil debe ser un archivo PDF.')
            except AttributeError:
                raise forms.ValidationError('El archivo adjunto no es válido.')
        else:
            raise forms.ValidationError('Es obligatorio adjuntar el documento mercantil.')
        
    def clean_latitud(self):
        latitud = self.cleaned_data.get('latitude')
        try:
            latitud_float = float(latitud)
            if not (-90 <= latitud_float <= 90):
                raise forms.ValidationError('La latitud debe estar en el rango de -90 a 90.')
        except ValueError:
            raise forms.ValidationError('La latitud debe ser un número válido.')
        return latitud

    def clean_longitud(self):
        longitud = self.cleaned_data.get('longitude')
        try:
            longitud_float = float(longitud)
            if not (-180 <= longitud_float <= 180):
                raise forms.ValidationError('La longitud debe estar en el rango de -180 a 180.')
        except ValueError:
            raise forms.ValidationError('La longitud debe ser un número válido.')
        return longitud
    
    def clean_horario(self):
        horario = self.cleaned_data.get('horario')
        try:
            inicio, fin = horario.split('-')
            hora_inicio, minuto_inicio = map(int, inicio.split(':'))
            hora_fin, minuto_fin = map(int, fin.split(':'))

            if not (0 <= hora_inicio <= 23 and 0 <= minuto_inicio <= 59):
                raise forms.ValidationError('El formato de inicio de horario no es válido.')
            if not (0 <= hora_fin <= 24 and 0 <= minuto_fin <= 59):
                raise forms.ValidationError('El formato de fin de horario no es válido.')
            if hora_inicio > hora_fin or (hora_inicio == hora_fin and minuto_inicio >= minuto_fin):
                raise forms.ValidationError('El horario de inicio debe ser anterior al horario de fin.')
        except (ValueError, AttributeError):
            raise forms.ValidationError('El formato de horario no es válido. Debe ser en formato HH:MM-HH:MM.')

        return horario

    def clean_imagen_qr(self):
        imagen_qr = self.cleaned_data.get('imagen_qr')
        if imagen_qr:
            try:
                if not imagen_qr.name.endswith('.png'):
                    raise forms.ValidationError('La imagen QR debe ser un archivo PNG.')
            except AttributeError:
                raise forms.ValidationError('El archivo adjunto no es válido.')
        else:
            raise forms.ValidationError('Es obligatorio adjuntar la imagen QR.')

    class Meta:
        model = User
        fields = ('username', 'nombreVendedor', 'cedula', 'password1', 'password2', 'nombreTienda', 'telefono', 'documentoMercantil','latitude', 'longitude', 'horario', 'productos', 'imagen_qr')

class RegistroClientesForm(forms.ModelForm):
    nombreCliente = forms.CharField(label="Nombre Completo")
    username = forms.CharField(label="Nombre de usuario")
    correo = forms.EmailField(validators=[EmailValidator(message='')])
    telefono = forms.CharField(label="Telefono")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirmación de contraseña")

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 != password2:
            raise forms.ValidationError(
                "Las contraseñas no coinciden"
            )
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está en uso.")
        return username
    
    def clean_correo(self):
        correo = self.cleaned_data['correo']
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return correo

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.isdigit() or len(telefono) != 10:
            raise forms.ValidationError('Ingresa un numero de telefono valido (ej: 3154043021)')
        return telefono

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
    correo = forms.EmailField(validators=[EmailValidator(message='')])
    imagen_qr = forms.ImageField(label="QR_Nequi", required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("El nombre de usuario ya está en uso.")
        return username

    def clean_correo(self):
        correo = self.cleaned_data['correo']
        if User.objects.filter(email=correo).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return correo
    
    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if not telefono.isdigit() or len(telefono) != 10:
            raise forms.ValidationError('Ingresa un numero de telefono valido (ej: 3154043021)')
        return telefono
    
    def clean_imagen_qr(self):
        imagen_qr = self.cleaned_data.get('imagen_qr')
        if imagen_qr:
            try:
                if not imagen_qr.name.endswith('.png'):
                    raise forms.ValidationError('La imagen QR debe ser un archivo PNG.')
            except AttributeError:
                raise forms.ValidationError('El archivo adjunto no es válido.')
        else:
            raise forms.ValidationError('Es obligatorio adjuntar la imagen QR.')
    class Meta:
        model = User
        fields = ('username', 'nombreTienda', 'telefono', 'latitude', 'longitude', 'horario', 'productos', 'correo', 'imagen_qr')



class ProductoForm(forms.ModelForm):
    nombreProd = forms.CharField(label="Nombre del producto")
    precioProd = forms.CharField(label="Precio del producto")
    descripcionProd = forms.CharField(label="Descripcion del producto")
    imagenProd = forms.ImageField(label="Imagen del producto")
    class Meta:
        model = Products
        fields = ['nombreProd', 'precioProd', 'descripcionProd', 'imagenProd']

class EditProductForm(forms.ModelForm):
    class Meta:
        model = Products
        fields = ['nombreProd', 'precioProd', 'descripcionProd', 'imagenProd']

class RegistroValidadorForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    email = forms.EmailField(validators=[EmailValidator(message='')])
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')