from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

# Create your views here.
def index(request):
    username = 'Daniel Caceres'
    return render(request, 'index.html', {'username' : username})

def login(request):
    return HttpResponse(render(request, 'login.html'))

def registro(request):
    return HttpResponse(render(request, 'registro.html'))