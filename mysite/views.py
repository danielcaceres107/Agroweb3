from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from agroweb import settings
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