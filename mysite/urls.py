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
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name="index"),
    path('login/', views.ingreso, name="login"),
    path('registro/', views.registro, name="registro"),
    path('mapa/', views.mapa, name="mapa"),
    path('mydata/',views.mydata, name="mydata"),
    path('logout/', views.signout, name='logout'),
    path('agregar/<int:producto_id>/<int:vendedor_id>', views.agregar_producto, name="Add"),
    path('eliminar/<int:producto_id>/<int:vendedor_id>', views.eliminar_producto, name="Del"),
    path('restar/<int:producto_id>/<int:vendedor_id>', views.restar_producto, name="Sub"),
    path('limpiar/', views.limpiar_carrito, name="Clean"),
    path('obtener_carrito/', views.get_carrito, name='GetCart'),
    path('enviar/', views.enviar_carrito, name="SendCart"),
    path('registroCliente/', views.registroCliente, name= 'registroCliente'),
    path('registroVendedor/', views.registroVendedor, name= 'registroVendedor'),
    path('perfil/', views.perfil, name='perfil'),
    path('editarPerfilV/', views.editarPerfilV, name='editarPerfilV'),
    path('editarPerfilC/', views.editarPerfilC, name='editarPerfilC'),
    path('actualizarUbicacion/', views.actualizarUbicacion, name='actualizarUbicacion'),
    path('registro-exitoso-vendedor/', views.registroExitosoVendedor, name='registroExitosoV'),
    path('validarVendedor/', views.validarVendedor, name="validarVendedores"),
    path('validar/<str:token>/', views.validarRegistro, name='validarRegistro'),
    path('denegar/<str:token>/', views.denegarRegistro, name='denegarRegistro'),
    path('crear_producto/', views.crear_producto, name='crear_producto'),
    path('aprobar_pedido/<int:pedido_id>/', views.aprobar_pedido, name='aprobarPedido'),
    path('denegar_pedido/<int:pedido_id>/', views.denegar_pedido, name='denegarPedido'),
    path('estado_pedidos', views.estado_pedidos, name='estadoPedidos'),
    path('cambiar_estado_pedido/<int:pedido_id>/', views.cambiar_estado_pedido, name='cambiarEstadoPedido'),
    path('editar_productos/', views.editar_productos, name='editar_productos'),
    path('edit_product/', views.editProduct, name='edit_product'),
    path('delete_product/', views.deleteProduct, name='delete_product'),
    path('new_edited_product/', views.NewEditedProduct, name='new_edited_product'),
    path('descargar/<str:url_archivo>/', views.descargar_archivo, name='descargar_archivo'),
    path('detalle_pedido/<int:pedido_id>/', views.detallePedido, name='detalle_pedido'),
    path('pago/', views.pago, name='pago'),
    path('efectivo/', views.efectivo, name='efectivo'),
    path('nequi/', views.nequi, name='nequi')
]