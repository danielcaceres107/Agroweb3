from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views import View
from agroweb import settings
from .models import DimVendedores
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
# Create your views here.


def index(request):
    key = settings.GOOGLE_MAPS_API_KEY
    context = {
        'key': key,
    }
    username = 'Daniel Caceres'
    return render(request, 'index.html', context)


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
