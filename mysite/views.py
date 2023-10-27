from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
import redis
from agroweb import settings
from mysite.my_context_processor import total_carrito
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
from django.db.models import Sum
import time


# Cargar las variables de entorno desde el archivo .env // el archivo .env no se sube a github
CORREO = config('CORREO')
CONTRASENA = config('CONTRASENA')



def index(request):
    if request.user.is_authenticated and request.user.username == "validador":
        # Usuario "validador"
        pedidos = Pedidos.objects.filter(proceso_validado=False)
        return render(request, 'validador.html', {'pedidos': pedidos})
    else:
        # Otros usuarios
        return render(request, 'index.html')
    
def aprobar_pedido(request, pedido_id):
    pedido = Pedidos.objects.get(pk=pedido_id)

    pedido.proceso_validado = True
    pedido.aprobado = True
    pedido.estado = 'en_camino'
    usuario = pedido.usuario_compra_id
    pedido.save()
    return redirect('index')

def denegar_pedido(request, pedido_id):
    pedido = Pedidos.objects.get(pk=pedido_id)

    pedido.proceso_validado = False
    pedido.aprobado = False
    pedido.estado = 'pendiente'
    pedido.save()
    return redirect('index')

def estado_pedidos(request):
    # Obtener todos los pedidos
    pedidos = Pedidos.objects.all()

    return render(request, 'estado_pedidos.html', {'pedidos': pedidos})

def cambiar_estado_pedido(request, pedido_id):
    if request.method == "POST":
        nuevo_estado = request.POST.get("nuevo_estado")
        
        try:
            pedido = Pedidos.objects.get(pk=pedido_id)
            pedido.estado = nuevo_estado
            pedido.save()
            return redirect('estadoPedidos')
        except Pedidos.DoesNotExist:
            # caso en que no se encuentre el pedido
            return redirect('estadoPedidos')
    
    # caso en que no sea una solicitud POST
    return redirect('estadoPedidos')


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
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()

    # Procesa tus datos y crea un HTML para las nuevas filas de la tabla del carrito 
    filas_html = ''
    for item_id, item_data in carrito_data.items():
        fila_html = f'<tr><td>{item_data["nombre"]}</td><td>{item_data["acumulado"]}</td><td>{item_data["cantidad"]}<button type="button" class="btn-agregar" data-producto="{item_data["last_product_id"]}" data-vendedor="{item_data["last_vendedor_id"]}">+</button><button type="button" class="btn-restar" data-producto="{{ value.producto_id }}" data-vendedor="{{ value.vendedor_id }}">-</button></td><td>{item_data["tienda"]}</td></tr>'
        filas_html += fila_html

    # Retorna los datos como una respuesta JSON
    return JsonResponse({'filas_html': filas_html})

@csrf_exempt
def enviar_carrito(request):
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()

    # Obtener el objeto User actual (usuario de compra)
    usuario_compra = request.user

    # monto total del pedido
    total_carrito_dic = total_carrito(request)  # Llama a la función del contexto procesador
    total_amount = Decimal(total_carrito_dic['total_carrito'])

    for item in carrito_data.values():
        acumulado = item['acumulado']
        cantidad = item['cantidad']
        producto = item['nombre']

    # Crear una nueva instancia de Pedido y guardarla en la base de datos
    nuevo_pedido = Pedidos.objects.create(
        usuario_compra_id=usuario_compra,
        total=total_amount,
        fecha=datetime.now()
    )

    # Inicializa una lista para almacenar los vendedores asociados al producto
    vendedores_list = []

    # Asignar los productos en el carrito a la nueva orden de pedido
    for item_id, item_data in carrito_data.items():
        last_product_id = int(item_data['last_product_id'])
        update_producto = Products.objects.get(id=last_product_id)
        nueva_cantidad = item_data['cantidad']
        ProductosPedidosConexion.objects.create(pedido=nuevo_pedido, producto=update_producto, cantidad=nueva_cantidad)
        
        # Obtener los vendedores asociados a este producto

        # Itera a través de los elementos en el carrito para encontrar vendedores para el producto dado, meterlos en una lista y agregar cada uno a VendedoresPedidosConexion

        # Agrega el vendedor a la lista si aún no está presente
        if item_data['vendedor_id'] not in vendedores_list:
            print("vendedor agregado en lista")
            vendedores_list.append(item_data['vendedor_id'])

        # Crear relaciones con los vendedores
        for vendedor_i in vendedores_list:
            VendedoresPedidosConexion.objects.create(pedido=nuevo_pedido, vendedor = Vendedores.objects.get(id=vendedor_i))

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

                r = redis.Redis(host='localhost', port=6379, db=0)

                # Genera un token único
                token = get_random_string(length=32)

                # Obtener los productos seleccionados del formulario
                productos_seleccionados = request.POST.getlist('productos')

                # Convierte la lista de productos a una cadena JSON
                productos_json = json.dumps(productos_seleccionados)

                print(productos_json)


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

                # Obtén los datos del formulario
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
                    'productos': productos_json
                }

                # Guarda los datos en Redis con el token como clave
                r.hmset(token, datos_vendedor)

                print(datos_vendedor)

                return render(request, 'msjValidarCorreo.html', {'mensaje': 'Estamos verificando la información proporcionada, al terminar esta validación podrás acceder a todos nuestros servicios.'})
            except IntegrityError:
                return render(request, 'registroVendedor.html', {"register": RegistroVendedorForm(), "error": "El nombre de usuario ya esta en uso, intente nuevamente."})
        else:
            return render(request, 'registroVendedor.html', {
                'register': RegistroVendedorForm(),
                "error": 'Contraseñas no coinciden'
            })

def validarVendedor(request):
    if request.user.is_authenticated:
        # Verifica si el usuario actual es un "validador"
        if request.user.username == "validador":
            r = redis.Redis(host='localhost', port=6379, db=0)
            # Recupera todos los tokens de registros pendientes
            tokens = r.keys('*')

            registros_pendientes = []

            for token in tokens:
                datos = r.hgetall(token)
                registros_pendientes.append({
                    'token': token.decode('utf-8'),
                    'username': datos[b'username'].decode('utf-8'),
                    'vendedor': datos[b'vendedor'].decode('utf-8'),
                    'cedula': datos[b'cedula'].decode('utf-8'),
                    'nombreTienda': datos[b'nombreTienda'].decode('utf-8'),
                    'telefono': datos[b'telefono'].decode('utf-8'),
                    'documentoMercantil': datos[b'documentoMercantil'].decode('utf-8'),
                    'latitude': datos[b'latitude'].decode('utf-8'),
                    'longitude': datos[b'longitude'].decode('utf-8'),
                    'horario': datos[b'horario'].decode('utf-8'),
                    'productos': datos[b'productos'].decode('utf-8'),
                })
            return render(request, 'validarVendedor.html', {'registros_pendientes': registros_pendientes})
        else:
            # Si el usuario no es "validador", redirige a la página msjValidarCorreo
            return render(request, 'msjValidarCorreo.html', {'mensaje': 'Estamos verificando la información proporcionada, al terminar esta validación podrás acceder a todos nuestros servicios.'})
    else:
        return HttpResponse('No tiene permiso para visualizar esta página')


def validarRegistro(request, token):
    r = redis.Redis(host='localhost', port=6379, db=0)

    datos_vendedor_redis = r.hgetall(token)

    if datos_vendedor_redis:

        datos_vendedor = {
            'username': datos_vendedor_redis[b'username'].decode('utf-8'),
            'password': datos_vendedor_redis[b'password'].decode('utf-8'),
            'vendedor': datos_vendedor_redis[b'vendedor'].decode('utf-8'),
            'cedula': datos_vendedor_redis[b'cedula'].decode('utf-8'),
            'nombreTienda': datos_vendedor_redis[b'nombreTienda'].decode('utf-8'),
            'telefono': datos_vendedor_redis[b'telefono'].decode('utf-8'),
            'documentoMercantil': datos_vendedor_redis[b'documentoMercantil'].decode('utf-8'),
            'latitude': datos_vendedor_redis[b'latitude'].decode('utf-8'),
            'longitude': datos_vendedor_redis[b'longitude'].decode('utf-8'),
            'horario': datos_vendedor_redis[b'horario'].decode('utf-8'),
            'productos': datos_vendedor_redis[b'productos'].decode('utf-8'),
        }
        
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

        # Convertir json en lista
        productos_lista = json.loads(datos_vendedor['productos'])

        # Establecer la relación muchos a muchos utilizando el método set()
        vendedor.productos.set(productos_lista)

        vendedor.save()

        # Enviar el correo electrónico de exito 
        smtp_host = 'smtp.office365.com'
        smtp_port = 587
        smtp_username = CORREO
        smtp_password = CONTRASENA
        sender = CORREO
        recipient = 'danielcaceres107@gmail.com'
        subject = 'Registro de ' + \
            datos_vendedor['vendedor'] + ' como vendedor Agroweb'
        message = '''
        <html>
        <head></head>
        <body>
            Estimado usuario, gracias por hacer parte de la comunidad de vendedores Agroweb, se realizara la validacion de los siguientes datos registrados:

            <h2>Registro del usuario ''' + datos_vendedor['vendedor'] + ''':</h2>
            <p><strong>Usuario: </strong> ''' + datos_vendedor['username'] + ''' </p>
            <p><strong>Nombre Completo: </strong> ''' + datos_vendedor['vendedor'] + ''' </p>
            <p><strong>Cedula: </strong> ''' + datos_vendedor['cedula'] + ''' </p>
            <p><strong>Nombre de la Tienda: </strong> ''' + datos_vendedor['nombreTienda'] + ''' </p>
            <p><strong>Celular: </strong> ''' + datos_vendedor['telefono'] + ''' </p>
            <p><strong>Horario de trabajo: </strong> ''' + datos_vendedor['horario'] + ''' </p> <br>

        </body>
        </html>
        '''

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient
        html_part = MIMEText(message, 'html')
        msg.attach(html_part)

        # Adjuntar el archivo PDF al mensaje
        if documento_adjunto:
            with open(documento_adjunto, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
                pdf_part = MIMEApplication(pdf_data, 'pdf')
                pdf_part.add_header('Content-Disposition', 'attachment',
                                    filename="registroMercantil_" + datos_vendedor['username'] + ".pdf")
                msg.attach(pdf_part)

        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.sendmail(sender, recipient, msg.as_string())

        # Eliminar los datos de la caché después de la validación
        r.delete(token)

        # Redirigir a una página de confirmación o mostrar un mensaje al usuario
        return HttpResponse(render(request, 'registroExitosoV.html'))
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
            cliente = Clientes.objects.get(usuarioCliente=request.user)
            # Obtener los últimos 5 pedidos del usuario vendedor
            ultimas_compras = Pedidos.objects.filter(usuario_compra_id=request.user).order_by('-fecha')[:5]
            
            # Crear una lista para almacenar los productos relacionados con los pedidos del cliente
            productos_comprados = []

            for pedido in ultimas_compras:
                productos_pedido = ProductosPedidosConexion.objects.filter(pedido=pedido)
                for producto_pedido in productos_pedido:
                    producto = producto_pedido.producto
                    cantidad = producto_pedido.cantidad
                    productos_comprados.append((producto, cantidad))

            return render(request, 'perfil.html', {'cliente': cliente, 'productos_comprados': productos_comprados, 'ultimas_compras': ultimas_compras})
        except Clientes.DoesNotExist:
            try:
                vendedor = Vendedores.objects.get(usuarioVendedor=request.user)

                # Obtener los últimos 5 pedidos del usuario vendedor
                ultimas_ventas = Pedidos.objects.filter(vendedor_pedido_id=vendedor).order_by('-fecha')[:5]

                # Crear una lista para almacenar los productos relacionados con los pedidos del cliente
                productos_vendidos = []

                productos_vendidos_total = 0

                list_productos_vendidos_total = calcular_productos_vendidos(vendedor)

                for producto, cantidad in list_productos_vendidos_total.items():
                    productos_vendidos_total += cantidad

                for pedido in ultimas_ventas:
                    productos_pedido = ProductosPedidosConexion.objects.filter(pedido=pedido)
                    for producto_pedido in productos_pedido:
                        producto = producto_pedido.producto
                        cantidad = producto_pedido.cantidad
                        productos_vendidos.append((producto, cantidad))

                return render(request, 'perfil.html', {'vendedor': vendedor, 'productos_vendidos': productos_vendidos, 'ultimas_ventas': ultimas_ventas, 'productos_vendidos_total': productos_vendidos_total })
            except Vendedores.DoesNotExist:
                    return render(request, 'perfil.html', {})
    else:
        return render(request, 'perfil.html', {})


def calcular_productos_vendidos(vendedor):
    # Inicializa un diccionario para rastrear la cantidad de productos vendidos por cada producto
    productos_vendidos_total = {}

    # Obtén todos los pedidos relacionados con este vendedor
    pedidos_vendedor = Pedidos.objects.filter(vendedor_pedido_id=vendedor)

    # Recorre cada pedido
    for pedido in pedidos_vendedor:
        productos_pedido = ProductosPedidosConexion.objects.filter(pedido=pedido)

        # Recorre cada producto en el pedido
        for producto_pedido in productos_pedido:
            producto = producto_pedido.producto
            cantidad = producto_pedido.cantidad

            # Actualiza el contador de productos vendidos para este producto
            if producto.pk in productos_vendidos_total:
                productos_vendidos_total[producto.pk] += cantidad
            else:
                productos_vendidos_total[producto.pk] = cantidad

    return productos_vendidos_total

    
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
            vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)
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
        productForm = ProductoForm()

    return render(request, 'crear_producto.html', {'productForm': productForm})
