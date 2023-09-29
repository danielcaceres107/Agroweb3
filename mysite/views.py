from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from agroweb import settings
from .models import Vendedores, Clientes, Products, Pedidos, ProductosPedidosConexion, VendedoresPedidosConexion
from .carrito import Carrito
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
import json
from .forms import ProductoForm, RegistroVendedorForm, RegistroClientesForm
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect
from .forms import EditarPerfilForm
from django.views.decorators.csrf import csrf_exempt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from decouple import config
from django.utils.crypto import get_random_string
from django.core.cache import cache
from django.urls import reverse
import os
import tempfile
from django.core.files.base import ContentFile
from datetime import datetime

# Cargar las variables de entorno desde el archivo .env // el archivo .env no se sube a github
CORREO = config('CORREO')
CONTRASENA = config('CONTRASENA')

def index(request):
    return HttpResponse(render(request, 'index.html'))


def mapa(request):
    key = settings.GOOGLE_MAPS_API_KEY
    context = {
        'key': key,
    }
    return render(request, 'mapa.html', context)

# logica carrito en mapa
@csrf_exempt
def agregar_producto(request, producto_id, vendedor_id):
    try:
        # Obtener el vendedor
        vendedor = Vendedores.objects.get(id=vendedor_id)
        # desde el vendedor obtener la tienda
        tienda = vendedor.nombreTienda
        print("nombreTienda: " + tienda)
    except Vendedores.DoesNotExist:
        return redirect('mapa')

    try:
        # Obtener el producto específico del vendedor
        producto = vendedor.productos.get(id=producto_id)
    except Products.DoesNotExist:
        # Producto no encontrado en la tienda del vendedor
        return redirect('mapa')

    # Agregar el producto al carrito
    carrito = Carrito(request)
    carrito.agregar(producto, vendedor_id, tienda)

    return JsonResponse({'message': 'Producto agregado al carrito'})



@csrf_exempt 
def eliminar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.eliminar(producto)
    return redirect('mapa')

@csrf_exempt 
def restar_producto(request, producto_id, vendedor_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.restar(producto, vendedor_id)
    return redirect('mapa')

@csrf_exempt 
def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.limpiar()
    return redirect('mapa')

@csrf_exempt
def get_carrito(request):
    # se debe obtener la información del carrito para actualizar el carrito al instante (aun no funciona)
    # buscar la manera de obtener lo que hay en carrito.html y modificar su contenido
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()
    print(carrito_data)

    carrito_html = {
        'carrito': carrito,
    }
    
    return render(request, 'carrito.html', carrito_html)

@csrf_exempt
def enviar_carrito(request):
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()

    # Obtener el objeto User actual (usuario de compra)
    usuario_compra = request.user

    # Calcular el monto total del pedido basado en los productos en el carrito
    total_amount = sum(item['acumulado'] * item['cantidad'] for item in carrito_data.values())

    # Crear una nueva instancia de Pedido y guardarla en la base de datos
    nuevo_pedido = Pedidos.objects.create(
        usuario_compra=usuario_compra,
        total=total_amount,
        fecha=datetime.now()
    )

    # Inicializa una lista para almacenar los vendedores asociados al producto
    vendedores_list = []

    # Asignar los productos en el carrito a la nueva orden de pedido
    for item_id, item_data in carrito_data.items():
        producto = Products.objects.get(id=item_id)
        cantidad = item_data['cantidad']
        ProductosPedidosConexion.objects.create(pedido=nuevo_pedido, producto=producto, cantidad=cantidad)
        
        # Obtener los vendedores asociados a este producto

        # Itera a través de los elementos en el carrito para encontrar vendedores para el producto dado, meterlos en una lista y agregar cada uno a VendedoresPedidosConexion

        # Agrega el vendedor a la lista si aún no está presente
        if item_data['vendedor_id'] not in vendedores_list:
            print("vendedor agregado en lista")
            vendedores_list.append(item_data['vendedor_id'])

        print(vendedores_list)
        # Crear relaciones con los vendedores
        for vendedor_i in vendedores_list:
            print(vendedor_i)
            VendedoresPedidosConexion.objects.create(pedido=nuevo_pedido, vendedor = Vendedores.objects.get(id=vendedor_i))

    enviar_correo(carrito_data, usuario_compra)
    carrito.limpiar()

    return redirect('mapa')

# correo del carrito
def enviar_correo(carrito_data, usuario):
    # Configurar los datos del correo
    remitente = CORREO
    destinatario = ["danielcaceres107@gmail.com",
                    "fowxd7@gmail.com", usuario.email]
    asunto = 'Datos del carrito'

    # Crear el cuerpo del mensaje
    cuerpo = "Estimado usuario " + usuario.username + ", gracias por comprar en Agroweb, los datos de su compra son:\n\n"
    for key, value in carrito_data.items():
        nombre = value['nombre']
        acumulado = value['acumulado']
        tienda = value['tienda']
        cuerpo += f"Producto: {nombre}\n"
        cuerpo += f"Acumulado: {acumulado}\n"
        cuerpo += f"Tienda: {tienda}\n\n"

    # Crear el objeto del mensaje
    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = ', '.join(destinatario)
    mensaje['Subject'] = asunto

    # Agregar el cuerpo del mensaje
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    # Enviar el correo utilizando el servidor SMTP de Office 365
    servidor_smtp = smtplib.SMTP('smtp.office365.com', 587)
    servidor_smtp.starttls()
    servidor_smtp.login(remitente, CONTRASENA)
    servidor_smtp.send_message(mensaje)
    servidor_smtp.quit()

# login
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
            return render(request, 'login.html', {"form": AuthenticationForm, "error": "Credenciales inválidas, por favor intente nuevamente"})


def registro(request):
    return HttpResponse(render(request, 'registro.html'))


@login_required
def signout(request):
    logout(request)
    return redirect('index')


@login_required
def mydata(request):

    vendedores = Vendedores.objects.all()

    # Crear una lista de diccionarios para almacenar la información de cada vendedor y sus productos
    data = []

    # Iterar sobre los vendedores y crear un diccionario con su información y la de sus productos
    for vendedor in vendedores:
        vendedor_data = {
            'model': 'mysite.Vendedores',
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
                'model': 'mysite.Products',
                'pk': producto.id,
                'fields': {
                    'nombreProd': producto.nombreProd,
                    # Convertir el decimal a una cadena de caracteres
                    'precio': float(producto.precioProd),
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

                # Generar un token único
                token = get_random_string(length=32)

                # Obtener los productos seleccionados del formulario
                productos_seleccionados = request.POST.getlist('productos')

                # Obtener la ruta de la carpeta de archivos temporales
                ruta_temporal = tempfile.gettempdir()

                # Obtener el archivo adjunto
                documento_adjunto = request.FILES.get('documentoMercantil')

                if documento_adjunto:
                    # Generar una ruta única para guardar el archivo
                    archivo_path = os.path.join(ruta_temporal, documento_adjunto.name)
                    with open(archivo_path, 'wb') as file:
                        for chunk in documento_adjunto.chunks():
                            file.write(chunk)
                else:
                    archivo_path = None

                # Guardar los datos en caché con el token como clave
                datos_vendedor = {
                    'username': request.POST['username'],
                    'vendedor': request.POST['nombreVendedor'],
                    'password': request.POST['password1'],
                    'cedula': request.POST['cedula'],
                    'nombreTienda': request.POST['nombreTienda'],
                    'telefono': request.POST['telefono'],
                    'documentoMercantil': archivo_path,
                    'latitude': request.POST['latitude'],
                    'longitude': request.POST['longitude'],
                    'horario': request.POST['horario'],
                    'productos': productos_seleccionados
                }

                # Guardar los datos en caché con el token como clave
                cache.set(token, datos_vendedor)

                # Generar el enlace de validación
                enlace_validacion = request.build_absolute_uri(
                    reverse('validarRegistro', args=[token]))

                # Enviar el correo electrónico de validación
                smtp_host = 'smtp.office365.com'
                smtp_port = 587
                smtp_username = CORREO
                smtp_password = CONTRASENA
                sender = CORREO
                recipient = 'danielcaceres107@gmail.com'
                subject = 'Registro de ' + \
                    request.POST['nombreVendedor'] + ' como vendedor Agroweb'
                message = '''
                <html>
                <head></head>
                <body>
                    Estimado usuario, gracias por hacer parte de la comunidad de vendedores Agroweb, se realizara la validacion de los siguientes datos registrados:

                    <h2>Registro del usuario ''' + request.POST['nombreVendedor'] + ''' para revision :</h2>
                    <p><strong>Usuario: </strong> ''' + request.POST['username'] + ''' </p>
                    <p><strong>Nombre Completo: </strong> ''' + request.POST['nombreVendedor'] + ''' </p>
                    <p><strong>Cedula: </strong> ''' + request.POST['cedula'] + ''' </p>
                    <p><strong>Nombre de la Tienda: </strong> ''' + request.POST['nombreTienda'] + ''' </p>
                    <p><strong>Celular: </strong> ''' + request.POST['telefono'] + ''' </p>
                    <p><strong>Horario de trabajo: </strong> ''' + request.POST['horario'] + ''' </p> <br>

                    <a href="{}" style="background-color: blue; border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer;">Validar Registro</a>
                </body>
                </html>
                '''.format(enlace_validacion)

                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = recipient
                html_part = MIMEText(message, 'html')
                msg.attach(html_part)

                # Adjuntar el archivo PDF al mensaje
                if documento_adjunto:
                    documento_adjunto.seek(0)
                    pdf_data = documento_adjunto.read()
                    pdf_part = MIMEApplication(pdf_data, 'pdf')
                    pdf_part.add_header('Content-Disposition', 'attachment',
                                        filename="registroMercantil_"+request.POST['username']+".pdf")
                    msg.attach(pdf_part)

                with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_username, smtp_password)
                    smtp.sendmail(sender, recipient, msg.as_string())

                return render(request, 'msjValidarCorreo.html', {'mensaje': 'Estamos verificando la información proporcionada, al terminar está validacion podrás acceder a todos nuestros servicios.'})
            except IntegrityError:
                return render(request, 'registroVendedor.html', {"register": RegistroVendedorForm(), "error": "El nombre de usuario ya esta en uso, intente nuevamente."})
        else:
            return render(request, 'registroVendedor.html', {
                'register': RegistroVendedorForm(),
                "error": 'Contraseñas no coinciden'
            })


def validarRegistro(request, token):
    # Verificar si el token es válido y existe en la caché
    datos_vendedor = cache.get(token)

    if datos_vendedor:
        # Guardar los datos del vendedor en la base de datos
        user = User.objects.create_user(
            username=datos_vendedor['username'], password=datos_vendedor['password'])
        user.save()

        # Crear un nuevo registro en la tabla DimVendedores
        vendedor = Vendedores(
            nombreVendedor=datos_vendedor['vendedor'],
            usuarioVendedor=datos_vendedor['username'],
            nombreTienda=datos_vendedor['nombreTienda'],
            cedula=datos_vendedor['cedula'],
            telefono=datos_vendedor['telefono'],
            latitude=datos_vendedor['latitude'],
            longitude=datos_vendedor['longitude'],
            horario=datos_vendedor['horario']
        )

        # Guardar el archivo PDF en el campo documentoMercantil
        documento_adjunto = datos_vendedor['documentoMercantil']
        if documento_adjunto:
            with open(documento_adjunto, 'rb') as file:
                archivo_pdf = file.read()
            archivo_pdf_data = ContentFile(archivo_pdf)
            vendedor.documentoMercantil.save('registroMercantil.pdf', archivo_pdf_data, save=True)

        vendedor.save()

        # Establecer la relación muchos a muchos utilizando el método set()
        vendedor.productos.set(datos_vendedor['productos'])

        # Autenticar y realizar el inicio de sesión con el backend predeterminado (?)
        # user = authenticate(
        #    request, username=datos_vendedor['username'], password=datos_vendedor['password1'])
        # login(request, user)

        print('usuario creado satisfactoriamente')

        # Eliminar los datos de la caché después de la validación
        cache.delete(token)

        # Redirigir a una página de confirmación o mostrar un mensaje al usuario
        return HttpResponse(render(request, 'mapa.html'))
    else:
        # Redirigir a una página de error o mostrar un mensaje de token inválido
        return HttpResponse('Token inválido')


def registroExitosoVendedor(request):
    return HttpResponse(render(request, 'registroExitosoV.html'))


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
                    username=request.POST['username'], password=request.POST['password1'], email=request.POST['correo'])
                user.save()

                # Crear un nuevo registro en la tabla DimClientes
                cliente = Clientes(
                    usuarioCliente=request.POST['username'],
                    nombreCliente=request.POST['nombreCliente'],
                    correo=request.POST['correo']
                )

                cliente.save()

                # Autenticar y realizar el inicio de sesión con el backend predeterminado
                user = authenticate(
                    request, username=request.POST['username'], password=request.POST['password1'])
                login(request, user)

                # Código para enviar el correo electrónico
                smtp_host = 'smtp.office365.com'
                smtp_port = 587
                smtp_username = CORREO
                smtp_password = CONTRASENA
                sender = CORREO
                recipient = request.POST['correo']
                subject = 'Registro de ' + \
                    request.POST['nombreCliente'] + ' como cliente Agroweb'
                message = '''
                <html>
                <head></head>
                <body>
                    <h2>¡Registro exitoso!</h2>
                    <p>Hola,</p>
                    <p>Tu registro como cliente Agroweb ha sido exitoso.</p>
                    <p>¡Gracias por unirte a nuestro sitio!</p>
                </body>
                </html>
                '''

                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = recipient
                html_part = MIMEText(message, 'html')
                msg.attach(html_part)

                with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_username, smtp_password)
                    smtp.sendmail(sender, recipient, msg.as_string())

                print('usuario creado satisfactoriamente')
                return redirect('mapa')
            except IntegrityError:
                return render(request, 'registroCliente.html', {"register": RegistroClientesForm(), "error": "Username already exists."})
        else:
            return render(request, 'registroCliente.html', {
                'register': RegistroClientesForm(),
                "error": 'Contraseñas no coinciden'
            })

def perfil(request):
    if request.user.is_authenticated:
        try:
            vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)
            return render(request, 'perfil.html', {'vendedor': vendedor})
        except Vendedores.DoesNotExist:
            try:
                cliente = Clientes.objects.get(usuarioCliente=request.user.username)
                return render(request, 'perfil.html', {'cliente': cliente})
            except Clientes.DoesNotExist:
                return render(request, 'perfil.html', {})
    else:
        return render(request, 'perfil.html', {})
    
def editarPerfilV(request):
    if request.method == 'POST':

        vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)

        # Recorrer los campos del formulario
        for field in request.POST:
            if field != 'csrfmiddlewaretoken' and field != 'username':
                value = request.POST.get(field)
                # Verificar si el campo tiene un valor
                if value:
                    setattr(vendedor, field, value)  # Actualizar el campo con el valor del formulario

        # Guardar los cambios en la base de datos
        vendedor.save()

        # Redireccionar a una página de Miperfil
        return render(request, 'perfil.html')

    else:
        # Obtener el objeto vendedor del usuario actual
        vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)

    return render(request, 'editarPerfilV.html', {'vendedor': vendedor})
    
def editarPerfilC(request):
    if request.method == 'POST':
        cliente = Clientes.objects.get(usuarioCliente=request.user.username)
        
        # Recorrer los campos del formulario
        for field in request.POST:
            if field != 'csrfmiddlewaretoken' and field != 'username':
                value = request.POST.get(field)
                # Verificar si el campo tiene un valor
                if value:
                    setattr(cliente, field, value)  # Actualizar el campo con el valor del formulario

        # Guardar los cambios en la base de datos
        cliente.save()

        # Redireccionar a una página de Miperfil
        return render(request, 'perfil.html')
    else:
        # Obtener el objeto cliente del usuario actual
        cliente = Clientes.objects.get(usuarioCliente=request.user.username)
    return render(request, 'editarPerfilC.html', {'cliente': cliente})

@csrf_exempt
def actualizarUbicacion(request):
    if request.method == 'POST':
        latitude = request.POST.get('latitude', None)
        longitude = request.POST.get('longitude', None)
        try:
            vendedor = Vendedores.objects.get(
                usuarioVendedor=request.user.username)
            vendedor.latitude = latitude
            vendedor.longitude = longitude
            vendedor.save()
            return JsonResponse({'message': 'Ubicación actualizada correctamente.'})
        except Vendedores.DoesNotExist:
            return JsonResponse({'message': 'No se encontró el vendedor.'})
    else:
        return JsonResponse({'message': 'Método no permitido.'})
    
def crear_producto(request):
    if request.method == 'POST':
        productForm = ProductoForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
            print('producto agregado en la BD')
            # Realizar alguna acción adicional después de guardar el producto
            return render(request, 'msjProductoRegistrado.html')
        else:
            print(productForm.errors)  # Muestra los errores en la consola
    else:
        print('no entra')
        productForm = ProductoForm()

    return render(request, 'crear_producto.html', {'productForm': productForm})
