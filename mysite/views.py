from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from agroweb import settings
from .models import Vendedores, Clientes, Products
from .carrito import Carrito
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
import json
from .forms import RegistroVendedorForm, RegistroClientesForm
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

# Cargar las variables de entorno desde el archivo .env // el archivo .env no se sube a github
CORREO = config('CORREO')
CONTRASENA = config('CONTRASENA')

# Create your views here.


def index(request):
    return HttpResponse(render(request, 'index.html'))


def mapa(request):
    key = settings.GOOGLE_MAPS_API_KEY
    context = {
        'key': key,
    }
    return render(request, 'mapa.html', context)

# logica carrito en mapa


def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.agregar(producto)

    return redirect("mapa")


def eliminar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.eliminar(producto)
    return redirect("mapa")


def restar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.restar(producto)
    return redirect("mapa")


def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.limpiar()
    return redirect("mapa")


def enviar_carrito(request):
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()

    # Obtener el objeto User actual
    usuario = request.user

    enviar_correo(carrito_data, usuario)
    carrito.limpiar()
    return redirect("mapa")

# correo del carrito


def enviar_correo(carrito_data, usuario):
    # Configurar los datos del correo
    remitente = CORREO
    destinatario = ["danielcaceres107@gmail.com",
                    "fowxd7@gmail.com", usuario.email]
    asunto = 'Datos del carrito'

    # Crear el cuerpo del mensaje
    cuerpo = "Compra en agroweb de " + usuario.username + ":\n\n"
    for key, value in carrito_data.items():
        nombre = value['nombre']
        acumulado = value['acumulado']
        cuerpo += f"Nombre: {nombre}\n"
        cuerpo += f"Acumulado: {acumulado}\n\n"

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
                recipient = 'fowxd7@gmail.com'
                subject = 'Registro de ' + \
                    request.POST['username'] + ' como vendedor Agroweb'
                message = '''
                <html>
                <head></head>
                <body>
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
                    pdf_part = MIMEApplication(documento_adjunto.read(), 'pdf')
                    pdf_part.add_header('Content-Disposition', 'attachment',
                                        filename='documento.pdf')
                    msg.attach(pdf_part)

                with smtplib.SMTP(smtp_host, smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_username, smtp_password)
                    smtp.sendmail(sender, recipient, msg.as_string())

                return HttpResponse('Correo enviado para validar')
            except IntegrityError:
                return render(request, 'registroVendedor.html', {"register": RegistroVendedorForm(), "error": "Username already exists."})
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
            archivo_pdf = ContentFile(documento_adjunto.read())
            vendedor.documentoMercantil.save(documento_adjunto.name, archivo_pdf, save=True)

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
                    request.POST['username'] + ' como cliente Agroweb'
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
            vendedor = Vendedores.objects.get(
                usuarioVendedor=request.user.username)
            return render(request, 'perfil.html', {'vendedor': vendedor})
        except Vendedores.DoesNotExist:
            try:
                cliente = Clientes.objects.get(
                    usuarioCliente=request.user.username)
                return render(request, 'perfil.html', {'cliente': cliente})
            except Clientes.DoesNotExist:
                return render(request, 'perfil.html', {})
    else:
        return render(request, 'perfil.html', {})


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
