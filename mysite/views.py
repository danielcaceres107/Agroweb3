from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views import View
from agroweb import settings
from .models import DimVendedores, DimClientes
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.core import serializers
import json
from .forms import RegistroVendedorForm, RegistroClientesForm
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect
from .forms import EditarPerfilForm

# Create your views here.


def index(request):
    return HttpResponse(render(request, 'index.html'))


def mapa(request):
    key = settings.GOOGLE_MAPS_API_KEY
    context = {
        'key': key,
    }
    return render(request, 'mapa.html', context)


def ingreso(request):
    if request.method == 'GET':
        return render(request, 'login.html', {"form": AuthenticationForm})
    else:
        user = authenticate(
            request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'login.html', {"form": AuthenticationForm, "error": "Username or password is incorrect."})


def registro(request):
    return HttpResponse(render(request, 'registro.html'))


@login_required
def signout(request):
    logout(request)
    return redirect('index')


@login_required
def mydata(request):

    vendedores = DimVendedores.objects.all()

    # Crear una lista de diccionarios para almacenar la información de cada vendedor y sus productos
    data = []

    # Iterar sobre los vendedores y crear un diccionario con su información y la de sus productos
    for vendedor in vendedores:
        vendedor_data = {
            'model': 'miapp.dimvendedores',
            'pk': vendedor.id,
            'fields': {
                'nombreVendedor': vendedor.nombreVendedor,
                'latitude': vendedor.latitude,
                'longitude': vendedor.longitude,
                'nombreTienda': vendedor.nombreTienda,
                'telefono': vendedor.telefono,
                'horario': vendedor.horario,
            }
        }
        # Obtener los productos de cada vendedor y agregarlos al diccionario
        productos = []
        for producto in vendedor.productos.all():
            productos.append({
                'model': 'miapp.dimproductos',
                'pk': producto.id,
                'fields': {
                    'nombreProd': producto.nombreProd,
                    # Convertir el decimal a una cadena de caracteres
                    'precio': str(producto.precioProd),
                    'descripcion': producto.descripcionProd,
                    'imagenProdUrl': request.build_absolute_uri('/static' + producto.imagenProd.url)
                }
            })
        vendedor_data['productos'] = productos
        data.append(vendedor_data)

    # Crear un diccionario que contenga los datos de los vendedores y sus productos
    result_dict = {
        'vendedores': data
    }

    # Convertir el diccionario en un objeto JSON
    result_json = json.dumps(
        result_dict, cls=DjangoJSONEncoder, default=decimal_default)

    return HttpResponse(result_json, content_type='application/json')


# Función para convertir los objetos Decimal en una representación serializable
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError("Object of type '%s' is not JSON serializable" %
                    type(obj)._name_)


def registroVendedor(request):
    if request.method == 'GET':
        return render(request, 'registroVendedor.html', {
            # utiliza la instancia del formulario personalizado
            'register': RegistroVendedorForm()
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                    username=request.POST['username'], password=request.POST['password1'])
                user.save()

                # Crear un nuevo registro en la tabla DimVendedores
                vendedor = DimVendedores(
                    nombreVendedor=request.POST['nombreVendedor'],
                    cedula=request.POST['cedula'],
                    nombreTienda=request.POST['nombreTienda'],
                    telefono=request.POST['telefono'],
                    latitude=request.POST['latitude'],
                    longitude=request.POST['longitude'],
                    horario=request.POST['horario']
                )
                print(vendedor)
                vendedor.save()

                # Obtener los productos seleccionados del formulario
                productos_seleccionados = request.POST.getlist('productos')

                # Establecer la relación muchos a muchos utilizando el método set()
                vendedor.productos.set(productos_seleccionados)

                # Autenticar y realizar el inicio de sesión con el backend predeterminado
                user = authenticate(
                    request, username=request.POST['username'], password=request.POST['password1'])
                login(request, user)

                print('usuario creado satisfactoriamente')
                return redirect('mapa')
            except IntegrityError:
                return render(request, 'registroVendedor.html', {"register": RegistroVendedorForm(), "error": "Username already exists."})
        else:
            return render(request, 'registroVendedor.html', {
                'register': RegistroVendedorForm(),
                "error": 'Contraseñas no coinciden'
            })


def registroCliente(request):
    if request.method == 'GET':
        return render(request, 'registroCliente.html', {
            # utiliza la instancia del formulario personalizado
            'register': RegistroClientesForm()
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(
                    username=request.POST['username'], password=request.POST['password1'])
                user.save()

                # Crear un nuevo registro en la tabla DimClientes
                cliente = DimClientes(
                    usuarioCliente=request.POST['username'],
                    nombreCliente=request.POST['nombreCliente'],
                    correo=request.POST['correo']
                )
                print(cliente)
                cliente.save()

                # Autenticar y realizar el inicio de sesión con el backend predeterminado
                user = authenticate(
                    request, username=request.POST['username'], password=request.POST['password1'])
                login(request, user)

                print('usuario creado satisfactoriamente')
                return redirect('mapa')
            except IntegrityError:
                return render(request, 'registroCliente.html', {"register": RegistroClientesForm(), "error": "Username already exists."})
        else:
            return render(request, 'registroCliente.html', {
                'register': RegistroClientesForm(),
                "error": 'Contraseñas no coinciden'
            })

        

def editar_perfil(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('perfil')  # Redirigir a la página del perfil actualizado
    else:
        form = EditarPerfilForm(instance=request.user)
    return render(request, 'perfil.html', {'form': form})
