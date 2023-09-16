"""
URL configuration for agroweb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name="index"),
    path('login/', views.ingreso, name="login"),
    path('registro/', views.registro, name="registro"),
    path('mapa/', views.mapa, name="mapa"),
    path('mydata/',views.mydata, name="mydata"),
    path('logout/', views.signout, name='logout'),
    path('agregar/<int:producto_id>/', views.agregar_producto, name="Add"),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name="Del"),
    path('restar/<int:producto_id>/', views.restar_producto, name="Sub"),
    path('limpiar/', views.limpiar_carrito, name="Clean"),
    path('enviar/', views.enviar_carrito, name="SendCart"),
    path('registroCliente/', views.registroCliente, name= 'registroCliente'),
    path('registroVendedor/', views.registroVendedor, name= 'registroVendedor'),
    path('perfil/', views.perfil, name='perfil'),
    path('editarPerfilV/', views.editarPerfilV, name='editarPerfil'),
    path('editarPerfilC/', views.editarPerfilC, name='editarPerfil'),
    path('actualizarUbicacion/', views.actualizarUbicacion, name='actualizarUbicacion'),
    path('registro-exitoso-vendedor/', views.registroExitosoVendedor, name='registroExitosoV'),
    path('validar/<str:token>/', views.validarRegistro, name='validarRegistro'),
    path('crear_producto/', views.crear_producto, name='crear_producto')
]