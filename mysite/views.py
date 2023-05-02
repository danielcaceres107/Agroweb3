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
    result_list = list(DimVendedores.objects
                       .exclude(latitude__isnull=True)
                       .exclude(longitude__isnull=True)
                       .exclude(latitude__exact='')
                       .exclude(longitude__exact='')
                       .values('id',
                               'nombreVendedor',
                               'latitude',
                               'longitude',
                               'nombreTienda',
                               'telefono',
                               'horario',
                               ))

    return JsonResponse(result_list, safe=False)

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