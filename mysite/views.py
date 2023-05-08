from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views import View
from agroweb import settings
from .models import DimVendedores, DimProducts
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.core import serializers
import json
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
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'login.html', {"form": AuthenticationForm, "error": "Username or password is incorrect."})


def registro(request):
    if request.method == 'GET':
        return render(request, 'registro.html', {
            'register': UserCreationForm
        })
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'])
                user.save()
                login(request, user)
                print('usuario creado satisfactoriamente')
                return redirect('index')
            except IntegrityError:
                return render(request, 'registro.html', {"register": UserCreationForm, "error": "Username already exists."})
        else:
            return render(request, 'registro.html', {
            'register': UserCreationForm,
            "error": 'Contraseñas no coinciden'
            })


@login_required
def signout(request):
    logout(request)
    return redirect('index')

@login_required
def mydata(request):
    # Obtener todos los vendedores
    vendedores = DimVendedores.objects.prefetch_related('productos_venta')

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
        for producto in vendedor.productos_venta.all():
            productos.append({
                'model': 'miapp.dimproductos',
                'pk': producto.id,
                'fields': {
                    'nombreProd': producto.nombreProd,
                    'precio': producto.precioProd,
                    'descripcion': producto.descripcionProd,
                }
            })
        vendedor_data['productos'] = productos
        data.append(vendedor_data)

    # Crear un diccionario que contenga los datos de los vendedores y sus productos
    result_dict = {
        'vendedores': data
    }

    # Convertir el diccionario en un objeto JSON
    result_json = json.dumps(result_dict)

    return HttpResponse(result_json, content_type='application/json')

@require_POST
@login_required
def add_to_cart(request, product_id):
    product = DimProducts.objects.get(id=product_id)
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {
            'name': product.nombreProd,
            'price': str(product.precioProd),
            'quantity': 1,
        }
    request.session['cart'] = cart
    return redirect('cart')

@require_POST
@login_required
def add_to_cart(request, product_id):
    product = DimProducts.objects.get(id=product_id)
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += 1
    else:
        cart[str(product_id)] = {
            'name': product.nombreProd,
            'price': str(product.precioProd),
            'quantity': 1,
        }
    request.session['cart'] = cart
    return redirect('cart')