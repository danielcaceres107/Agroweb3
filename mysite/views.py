from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views import View
from agroweb import settings
from .models import DimVendedores
import googlemaps
import json
# Create your views here.
def index(request):
    key = settings.GOOGLE_MAPS_API_KEY
    context = {
        'key':key,
    }
    username = 'Daniel Caceres'
    return render(request, 'index.html', context)

def login(request):
    return HttpResponse(render(request, 'login.html'))

def registro(request):
    return HttpResponse(render(request, 'registro.html'))

def mydata(request):
    result_list = list(DimVendedores.objects\
                .exclude(latitude__isnull=True)\
                .exclude(longitude__isnull=True)\
                .exclude(latitude__exact='')\
                .exclude(longitude__exact='')\
                .values('id',
                        'nombreVendedor', 
                        'latitude',
                        'longitude',
                        'nombreTienda',
                        'telefono',
                        'correo',
                        ))
  
    return JsonResponse(result_list, safe=False)

class VendedorView(View):
    def get(self, request):
        vendedores = list(DimVendedores.objects.values())
        if len(vendedores) > 0:
            datos = {'message': "Success", 'nombreVendedor': vendedores}
        else:
            datos = {'message': "Vendedores not found..."}
        return JsonResponse(datos)
    
    def post(self, request):
        pass

    def put(self, request):
        pass