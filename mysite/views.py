from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import redis
from agroweb import settings
from mysite.my_context_processor import total_carrito
from .models import Vendedores, Clientes, Products, Pedidos, ProductosPedidosConexion, VendedoresPedidosConexion
from .carrito import Carrito
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
import json
from .forms import ProductoForm, RegistroVendedorForm, RegistroClientesForm, EditProductForm, RegistroValidadorForm
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.csrf import csrf_exempt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.contrib import messages
from django.urls import reverse
import os
from django.core.files.base import ContentFile
from datetime import datetime
from django.db.models import Sum
from twilio.rest import Client
import subprocess
import io


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
    pedido.estado = 'pagado'
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

def enviar_correos(usuario_email, asunto, cuerpo):
    intentos_maximos = 3
    intento_actual = 0

    while intento_actual <= intentos_maximos:
        try:
            # Crear el objeto del mensaje
            mensaje = MIMEMultipart()
            mensaje['From'] = settings.CORREO
            mensaje['To'] = usuario_email
            mensaje['Subject'] = asunto

            # Agregar el cuerpo del mensaje
            mensaje.attach(MIMEText(cuerpo, 'html'))

            # Enviar el correo utilizando el servidor SMTP de Office 365
            servidor_smtp = smtplib.SMTP('smtp.office365.com', 587)
            servidor_smtp.starttls()
            servidor_smtp.login(settings.CORREO, settings.CONTRASENA)
            servidor_smtp.send_message(mensaje)
            servidor_smtp.quit()

            # Si el correo se envía correctamente, sal del bucle
            break

        except Exception as e:
            intento_actual += 1
            if intento_actual == intentos_maximos:
                try:
                    send_mail(
                        asunto,
                        cuerpo,
                        settings.CORREO,
                        [usuario_email],
                        html_message=cuerpo,
                    )
                except:
                    print("Correo electrónico no se pudo enviar por send_mail.")
                    raise e  # Lanza la excepción si se alcanza el número máximo de intentos
            else:
                print(f"Intento {intento_actual}: Error al enviar el correo electrónico - {e}")

def cambiar_estado_pedido(request, pedido_id):
    if request.method == "POST":
        nuevo_estado = request.POST.get("nuevo_estado")
        
        try:
            pedido = Pedidos.objects.get(pk=pedido_id)
            pedido.estado = nuevo_estado
            pedido.save()

            email_comprador = pedido.usuario_compra_id.email
            print('email:', email_comprador)

            try:
                # Enviar correo de cambio de estado del pedido
                recipient = email_comprador
                subject = 'Informacion de su pedido en Agroweb'
                message = '''
                <html>
                <head></head>
                <body>
                    <h2>Cambio de estado en su pedido</h2>
                    <p>Buenas noticias,</p>
                    <p>El estado de su pedido ahora es: %s</p>
                    <p></p>
                    <p>Equipo de Agroweb</p>
                </body>
                </html>
                '''% nuevo_estado
                enviar_correos(recipient, subject, message)
                print("correo de cambio de estado enviado con exito")
            except:
                print("no se pudo enviar el correo de actualizacion de estado")
            if request.user.username == "validador":
                return redirect('estadoPedidos')
            else:
                return redirect('perfil')
        except Pedidos.DoesNotExist:
            print("no se encuentra el pedido")
            if request.user.username == "validador":
                return redirect('estadoPedidos')
            else:
                return redirect('perfil')
    
    if request.user.username == "validador": 
        return redirect('estadoPedidos')
    else:
        return redirect('perfil')
    

def detallePedido(request, pedido_id) :
    if request.method == "POST":
        pedido = Pedidos.objects.get(id=pedido_id)
        productos_pedidos_conn = ProductosPedidosConexion.objects.filter(pedido_id=pedido_id)
        # Obtener vendedores únicos asociados al pedido usando distinct()
        vendedores_pedidos_conn = VendedoresPedidosConexion.objects.filter(pedido_id=pedido_id).values('vendedor_id').distinct()
        # Obtener los objetos de vendedores correspondientes a los IDs
        vendedores_ids = [vendedor['vendedor_id'] for vendedor in vendedores_pedidos_conn]
        vendedores = Vendedores.objects.filter(id__in=vendedores_ids)
        products = Products.objects.all

    return render(request, 'detalle_pedido.html', {'pedido_id': pedido_id, 'productos_pedidos_conn': productos_pedidos_conn, 'products': products, 'pedido': pedido , 'vendedores' : vendedores})


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
        print("vendedor no encontrado")
        return redirect('mapa')

    try:
        # Obtener el producto específico del vendedor
        producto = vendedor.productos.get(id=producto_id)
    except Products.DoesNotExist:
        print("Producto no encontrado en la tienda del vendedor")
        return redirect('mapa')

    # Agregar el producto al carrito
    carrito = Carrito(request)
    carrito.agregar(producto, vendedor_id, tienda)

    return JsonResponse({'message': 'Producto agregado al carrito'})

@csrf_exempt 
def eliminar_producto(request, producto_id, vendedor_id):
    carrito = Carrito(request)
    producto = Products.objects.get(id=producto_id)
    carrito.eliminar(producto, vendedor_id)
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
        # Obtén la URL dinámicamente utilizando reverse
        url = reverse('Del', args=[item_data["producto_id"], item_data["vendedor_id"]])

        fila_html = f'<tr><td>{item_data["nombre"]}</td><td>{item_data["acumulado"]}</td><td><center>{item_data["cantidad"]}</center></td><td>{item_data["tienda"]}</td><td id="borrar-a">' + \
            f'<a href="{url}" class="btn-eliminar" data-producto="{item_data["producto_id"]}" data-vendedor="{item_data["vendedor_id"]}">Eliminar</a>' + \
            '</td></tr>'
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
    total_carrito_dic = total_carrito(request)  # Llama a la función de my_context_processor
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
    try:
        enviar_correo_carrito(carrito_data, usuario_compra)
    except:
        print("no se pudo enviar el correo del carrito")

    try:
        usuario = Clientes.objects.get(usuarioCliente=request.user.username)
    except ObjectDoesNotExist:
        # Si el usuario no se encuentra en Clientes, busca en Vendedores
        try:
            usuario = Vendedores.objects.get(usuarioVendedor=request.user.username)
        except ObjectDoesNotExist:
            # El usuario no se encuentra en ninguna de las dos tablas
            error_message = "Usuario inválido"
            return HttpResponse(error_message, status=400)

    account_sid = settings.ACCOUNT_SID
    auth_token= settings.AUTH_TOKEN

    if usuario:
        try:
            sms_carrito(usuario.telefono, account_sid, auth_token)
        except:
            print("no se pudo enviar el sms")
        try:
            llamada(usuario.telefono, account_sid, auth_token)
        except:
            print("no se pudo realizar la llamada")

    carrito.limpiar()

    return redirect('mapa')

def sms_carrito(telefono, account_sid, auth_token) :
    print("Enviando sms del SICC...")

    client = Client(account_sid, auth_token)
    message = client.messages.create(to="+57"+telefono,
                                from_="+4672500913",
                                body="Estimado Comprador agradecemos su compra en Agroweb ")
    print(message.sid)

def llamada(telefono, account_sid, auth_token) :
    print("Realizando llamada - MOnitorizacion SICC - SIT LTDA, Colombia")
    #mensa=input("Escriba el mensaje que desea enviar: ")
    #numero=input("Escriba numero de telefono con el signo + codigo del pais y telefono: ")
    
    client = Client(account_sid, auth_token)
    call = client.calls.create(url='https://handler.twilio.com/twiml/EH5bda876424d95b012cf33d73d3a90896',
                                    to='+57'+telefono,
                                    from_='+4672500913'
                                    )
    print(call.sid)
    print("Se realizara la llamada al numero elegido...Gracias")

# correo del carrito
def enviar_correo_carrito(carrito_data, usuario):
    # Configurar los datos del correo
    remitente = settings.CORREO
    destinatario = ['danielcaceres98@hotmail.com', usuario.email]
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
    servidor_smtp.login(remitente, settings.CONTRASENA)
    servidor_smtp.send_message(mensaje)
    servidor_smtp.quit()

# login
def ingreso(request):
    if request.method == 'GET':
        return render(request, 'login.html', {"form": AuthenticationForm})
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
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


def registroCliente(request):
    if request.method == 'GET':
        return render(request, 'registroCliente.html', {
            # utiliza la instancia del formulario personalizado
            'register': RegistroClientesForm()
        })
    else:
        form = RegistroClientesForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                    username=request.POST['username'], password=request.POST['password1'], email=request.POST['correo'])
            user.save()


            # Crear un nuevo registro en la tabla DimClientes
            cliente = Clientes(
                usuarioCliente=user.username,
                nombreCliente=form.cleaned_data['nombreCliente'],
                correo=form.cleaned_data['correo'],
                telefono=form.cleaned_data['telefono']
            )

            cliente.save()

            # Autenticar y realizar el inicio de sesión con el backend predeterminado
            user = authenticate(
                request, username=user.username, password=request.POST['password1'])
            login(request, user)
            try:
                # Enviar correo
                recipient = form.cleaned_data['correo']
                subject = 'Registro de ' + form.cleaned_data['nombreCliente'] + ' como cliente Agroweb'
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
                enviar_correos(recipient, subject, message)
            except:
                print("no se pudo enviar el correo de registro cliente")

            print('Usuario creado satisfactoriamente')
            return redirect('mapa')
        else:
            # Logica para mostrar los errores
            errors_dict = form.errors.as_data()
            username_error = ""
            email_error = ""
            telefono_error = ""
            password_error = ""

            # Itera sobre los errores del form
            for field, error_list in errors_dict.items():
                for error in error_list:
                    if 'username' in field:
                        username_error += error.message + ". "
                    elif 'correo' in field:
                        email_error += error.message + ". "
                    elif 'telefono' in field:
                        telefono_error += error.message + ". "
                    elif '__all__' in field:
                        password_error += error.message + ". "

            # Renderiza el formulario con los mensajes de error personalizados
            return render(request, 'registroCliente.html', {"register": form, "username_error": username_error, "email_error": email_error, "telefono_error" : telefono_error, "password_error": password_error})


def registroVendedor(request):
    if request.method == 'GET':
        return render(request, 'registroVendedor.html', {
            'register': RegistroVendedorForm()
        })
    else:
        form = RegistroVendedorForm(request.POST, request.FILES)
        if form.is_valid():
            username = request.POST['username']

            r = redis.Redis(host='localhost', port=6379, db=0)

            # Genera un token único
            token = get_random_string(length=32)

            # Obtener los productos seleccionados del formulario
            productos_seleccionados = request.POST.getlist('productos')

            # Convierte la lista de productos a una cadena JSON
            productos_json = json.dumps(productos_seleccionados)

            # Obtener la ruta de la carpeta de archivos temporales
            ruta_temporal = settings.TEMP_DIR

            if not os.path.exists(ruta_temporal):
                os.makedirs(ruta_temporal)

            # Obtener los archivos adjuntos
            documento_adjunto = request.FILES.get('documentoMercantil')
            qr_adjunto = request.FILES.get('imagen_qr')

            if documento_adjunto:
                # Generar una ruta única para guardar el archivo (Ej: tmp/midocumento)
                archivo_name = username + documento_adjunto.name
                archivo_path = os.path.join(ruta_temporal, archivo_name)
                try:
                    with open(archivo_path, 'wb') as file:
                        for chunk in documento_adjunto.chunks():
                            file.write(chunk)
                except Exception as e:
                    print("Error al guardar el archivo pdf:", e)
                    return render(request, 'registroVendedor.html', {"register": form, "otro_error": "Error, por favor cambiar el nombre del archivo"})
            else:
                archivo_path = None

             # Guardar el archivo adjunto de la imagen QR
            if qr_adjunto:
                try:
                    img_name = username + qr_adjunto.name
                    qr_path = os.path.join(ruta_temporal, img_name)
                    if os.path.exists(qr_path):
                        os.chmod(qr_path, 0o400) #Linux
                        comando = f"attrib +w {qr_path}" #Windows
                        # Ejecutar el comando en el cmd
                        subprocess.run(comando, shell=True)
                    with open(qr_path, 'wb') as file:
                        for chunk in qr_adjunto.chunks():
                            file.write(chunk)
                except Exception as e:
                    print("Error al guardar el archivo qr:", e)
                    return render(request, 'registroVendedor.html', {"register": form, "otro_error": "Error, por favor cambiar el nombre del archivo"})
                    
            else:
                qr_path = None

            if documento_adjunto is not None and qr_adjunto is not None:
                if os.path.exists(archivo_path):
                    os.chmod(archivo_path, 0o400)
            
            # Obtén los datos del formulario
            datos_vendedor = {
                'username': request.POST['username'],
                'vendedor': request.POST['nombreVendedor'],
                'password': request.POST['password1'],
                'cedula': request.POST['cedula'],
                'nombreTienda': request.POST['nombreTienda'],
                'correo': request.POST['correo'],
                'telefono': request.POST['telefono'],
                'documentoMercantil': archivo_path,
                'latitude': request.POST['latitude'],
                'longitude': request.POST['longitude'],
                'horario': request.POST['horario'],
                'productos': productos_json,
                'imagen_qr' : qr_path
            }

            # Guarda los datos en Redis con el token como clave
            r.hmset(token, datos_vendedor)

            try:
                enviar_correos(request.POST['correo'], "Registro en agroweb", "<h2>Gracias por inscribirte a nuestra plataforma</h2><br><p>El siguiente paso es revisar tus datos y se te enviará un correo cuando ya puedas ingresar en la plataforma</p>")
            except:
                print("no se puede enviar el correo de registro vendedor")

            return render(request, 'msjValidarCorreo.html', {'mensaje': 'Estamos verificando la información proporcionada, al terminar esta validación podrás acceder a todos nuestros servicios.'})
        else:
            # Captura los errores del formulario y los pasa a la plantilla
            errors_dict = form.errors.as_data()
            username_error = ""
            cedula_error = ""
            telefono_error = ""
            correo_error = ""
            password_error = ""
            documento_error = ""
            latitud_error = ""
            longitude_error = ""
            horario_error = ""
            qr_error = ""
            otro_error = "por favor verifica los datos ingresados "

            for field, error_list in errors_dict.items():
                for error in error_list:
                    if 'username' in field:
                        username_error += error.message + ". "
                    if 'cedula' in field:
                        cedula_error += error.message + ". "
                    elif 'telefono' in field:
                        telefono_error += error.message + ". "
                    elif 'correo' in field:
                        correo_error += error.message + ". "
                    elif '__all__' in field:
                        password_error += error.message + ". "
                    elif 'documentoMercantil' in field:
                        documento_error += error.message + ". "
                    elif 'latitud' in field:
                        latitud_error += error.message + ". "
                    elif 'longitude' in field:
                        longitude_error += error.message + ". "
                    elif 'horario' in field:
                        horario_error += error.message + ". "
                    elif 'imagen_qr' in field:
                        qr_error += error.message + ". "
                    else:
                        otro_error += error.message + ". "

            return render(request, 'registroVendedor.html', {"register": form, "username_error": username_error, "cedula_error" : cedula_error ,"telefono_error" : telefono_error ,"password_error": password_error, "correo_error": correo_error, "documento_error": documento_error, "latitud_error": latitud_error, "longitude_error": longitude_error, "horario_error": horario_error, "qr_error": qr_error, "otro_error": otro_error})

def descargar_archivo(request, url_archivo):
    
    # Verificar si el archivo existe
    if os.path.exists(url_archivo):
        # Abrir y leer el archivo
        with open(url_archivo, 'rb') as archivo:
            contenido = archivo.read()
        # Crear una respuesta HTTP con el contenido del archivo
        response = HttpResponse(contenido, content_type='application/pdf')
        # Establecer encabezados para forzar la descarga del archivo
        response['Content-Disposition'] = 'attachment; filename="documentoMercantil.pdf"'
        return response
    else:
        # Devolver una respuesta 404 si el archivo no existe
        return HttpResponse("Archivo no encontrado", status=404)

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
                imagen_qr = datos.get(b'imagen_qr', b'') #el qr es opcional
                registros_pendientes.append({
                    'token': token.decode('utf-8'),
                    'username': datos[b'username'].decode('utf-8'),
                    'vendedor': datos[b'vendedor'].decode('utf-8'),
                    'cedula': datos[b'cedula'].decode('utf-8'),
                    'nombreTienda': datos[b'nombreTienda'].decode('utf-8'),
                    'correo': datos[b'correo'].decode('utf-8'),
                    'telefono': datos[b'telefono'].decode('utf-8'),
                    'documentoMercantil': datos[b'documentoMercantil'].decode('utf-8'),
                    'latitude': datos[b'latitude'].decode('utf-8'),
                    'longitude': datos[b'longitude'].decode('utf-8'),
                    'horario': datos[b'horario'].decode('utf-8'),
                    'productos': datos[b'productos'].decode('utf-8'),
                    'imagen_qr': imagen_qr.decode('utf-8')
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
            'correo': datos_vendedor_redis[b'correo'].decode('utf-8'),
            'telefono': datos_vendedor_redis[b'telefono'].decode('utf-8'),
            'documentoMercantil': datos_vendedor_redis[b'documentoMercantil'].decode('utf-8'),
            'latitude': datos_vendedor_redis[b'latitude'].decode('utf-8'),
            'longitude': datos_vendedor_redis[b'longitude'].decode('utf-8'),
            'horario': datos_vendedor_redis[b'horario'].decode('utf-8'),
            'productos': datos_vendedor_redis[b'productos'].decode('utf-8'),
            'imagen_qr': datos_vendedor_redis[b'imagen_qr'].decode('utf-8')
        }
        
        # Guardar los datos del vendedor en la base de datos
        user = User.objects.create_user(
            username=datos_vendedor['username'], password=datos_vendedor['password'], email=datos_vendedor['correo'])
        user.save()


        # Crear un nuevo registro en la tabla DimVendedores
        vendedor = Vendedores(
            nombreVendedor=datos_vendedor['vendedor'],
            usuarioVendedor=datos_vendedor['username'],
            nombreTienda=datos_vendedor['nombreTienda'],
            cedula=datos_vendedor['cedula'],
            correo=datos_vendedor['correo'],
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
            nombre_archivo = 'registroMercantil_%s.pdf' % datos_vendedor['username']
            vendedor.documentoMercantil.save(nombre_archivo, archivo_pdf_data, save=True)

        # Guardar la imagen QR en el campo imagen_qr
        imagen_qr_adjunta = datos_vendedor['imagen_qr']
        if imagen_qr_adjunta:
            with open(imagen_qr_adjunta, 'rb') as f:
                imagen_qr_content = f.read()
            imagen_qr_file = io.BytesIO(imagen_qr_content)
            nombre_imagen = 'imagen_qr_%s.png' % datos_vendedor['username']
            vendedor.imagen_qr.save(nombre_imagen, imagen_qr_file, save=True) 

        # Convertir json en lista
        productos_lista = json.loads(datos_vendedor['productos'])

        # Establecer la relación muchos a muchos utilizando el método set()
        vendedor.productos.set(productos_lista)

        vendedor.save()

        try:
            # Enviar el correo electrónico de exito 
            smtp_host = 'smtp.office365.com'
            smtp_port = 587
            smtp_username = settings.CORREO
            smtp_password = settings.CONTRASENA
            sender = settings.CORREO
            recipient = settings.CORREO
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
        except:
            print("no se pudo enviar el correo de registro usuario exitoso")

        # Eliminar los datos de la caché después de la validación
        r.delete(token)

        return redirect('validarVendedores')
    else:
        # Redirigir a una página de error o mostrar un mensaje de token inválido
        return HttpResponse('Token inválido')

def denegarRegistro(request, token):
    # Conectarse a Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Eliminar los datos asociados al token
    r.delete(token)
    
    return redirect('validarVendedores')

def registroExitosoVendedor(request):
    return HttpResponse(render(request, 'registroExitosoV.html'))


def perfil(request):
    if request.user.is_authenticated:
        try:
            cliente = Clientes.objects.get(usuarioCliente=request.user)
            # Obtener los últimos 5 pedidos del usuario
            ultimos_pedidos = Pedidos.objects.filter(usuario_compra_id=request.user).order_by('-fecha')[:5]

            print(ultimos_pedidos)

            datos_pedidos = []
            for pedido in ultimos_pedidos:
                productos_pedido_conn = ProductosPedidosConexion.objects.filter(pedido_id=pedido.id)
                productos_en_pedido = []
                for pedidoprod in productos_pedido_conn:
                    producto = Products.objects.get(id=pedidoprod.producto_id)
                    productos_en_pedido.append({
                        'nombre': producto.nombreProd,
                        'cantidad': pedidoprod.cantidad,
                        'precio': producto.precioProd
                    })
                datos_pedidos.append({
                    'id': pedido.id,
                    'fecha': pedido.fecha,
                    'total': pedido.total,
                    'productos': productos_en_pedido
                })
            return render(request, 'perfil.html', {'cliente': cliente, 'ultimos_pedidos': datos_pedidos})
        except Clientes.DoesNotExist:
            try:
                vendedor = Vendedores.objects.get(usuarioVendedor=request.user)

                # Obtener los últimos 5 pedidos del usuario vendedor
                ultimas_ventas = Pedidos.objects.filter(vendedor_pedido_id=vendedor).order_by('-fecha')[:5]

                print(ultimas_ventas)

                # Crear una lista para almacenar los productos relacionados con los pedidos del cliente
                datos_pedidos = []

                productos_vendidos_total = 0

                list_productos_vendidos_total = calcular_productos_vendidos(vendedor)

                for producto, cantidad in list_productos_vendidos_total.items():
                    productos_vendidos_total += cantidad

                for pedido in ultimas_ventas:
                    productos_pedido_conn = ProductosPedidosConexion.objects.filter(pedido_id=pedido.id)
                    productos_en_pedido = []
                    for pedidoprod in productos_pedido_conn:
                        producto = Products.objects.get(id=pedidoprod.producto_id)
                        productos_en_pedido.append({
                            'nombre': producto.nombreProd,
                            'cantidad': pedidoprod.cantidad,
                            'precio': producto.precioProd
                        })
                    datos_pedidos.append({
                        'id': pedido.id,
                        'fecha': pedido.fecha,
                        'total': pedido.total,
                        'estado': pedido.estado,
                        'productos': productos_en_pedido
                    })
                return render(request, 'perfil.html', {'vendedor': vendedor, 'ultimas_ventas': datos_pedidos, 'productos_vendidos_total': productos_vendidos_total})
            except Vendedores.DoesNotExist:
                    return render(request, 'perfil.html', {})
    else:
        return render(request, 'perfil.html', {})


def calcular_productos_vendidos(vendedor):
    # Inicializa un diccionario para rastrear la cantidad de productos vendidos por cada producto
    productos_vendidos_total = {}

    # Obtener todos los pedidos relacionados con este vendedor
    pedidos_vendedor = Pedidos.objects.filter(vendedor_pedido_id=vendedor)

    # Recorrer cada pedido
    for pedido in pedidos_vendedor:
        productos_pedido = ProductosPedidosConexion.objects.filter(pedido=pedido)

        # Recorrer cada producto en el pedido
        for producto_pedido in productos_pedido:
            producto = producto_pedido.producto
            cantidad = producto_pedido.cantidad

            # Actualizar el contador de productos vendidos para este producto
            if producto.pk in productos_vendidos_total:
                productos_vendidos_total[producto.pk] += cantidad
            else:
                productos_vendidos_total[producto.pk] = cantidad

    return productos_vendidos_total

    
def editarPerfilV(request):
    if request.method == 'POST':

        vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)
        for field in request.POST.keys():
            if field != 'csrfmiddlewaretoken' and field != 'username':
                value = request.POST.get(field)
                # Verificar si el campo tiene un valor
                if value:
                    setattr(vendedor, field, value)  # Actualizar el campo con el valor del formulario

        messages.success(request, 'Perfil actualizado exitosamente')
        # Guardar los cambios en la base de datos
        vendedor.save()

        # Redireccionar a una página de Miperfil
        return redirect('perfil')

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

        messages.success(request, 'Perfil actualizado exitosamente')
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

@login_required
def crear_producto(request):
    if request.method == 'POST':
        productForm = ProductoForm(request.POST, request.FILES)
        if productForm.is_valid():
            producto = productForm.save()
            print('producto agregado en la BD')

            # agregar el producto al vendedor / usuario actual
            vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)
            vendedor.productos.add(producto)

            return render(request, 'msjProductoRegistrado.html')
        else:
            print(productForm.errors)  # Muestra los errores en la consola
    else:
        productForm = ProductoForm()

    return render(request, 'crear_producto.html', {'productForm': productForm})

@login_required
def editar_productos(request):
     # vendedor del usuario actual
    vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)

    # productos relacionados con el vendedor
    productos_relacionados = vendedor.productos.all()

    return render(request, 'editar_productos.html', {'productos': productos_relacionados})

@login_required
def editProduct(request):
    try:
        if request.method == 'POST':
            # Obtener el product_id desde el formulario
            product_id = request.POST.get('product_id')
            product = Products.objects.get(id=product_id)

            # Procesar el formulario de edición si se ha enviado
            form = EditProductForm(request.POST, instance=product)
            
            return render(request, 'edit_product.html', {'form': form, 'product': product})
        else:
            return redirect('editar_productos.html')       
    except Products.DoesNotExist:
        return render(request, 'error.html', {'error_message': 'Producto no encontrado'})

@login_required
def deleteProduct(request):
    if request.method == 'POST':
        # Obtener el product_id desde el formulario
        product_id = request.POST.get('product_id')

        try:
            # Obtener el producto a eliminar
            product = Products.objects.get(pk=product_id)
            product.delete()
            return redirect('editar_productos.html')

        except Products.DoesNotExist:
            # Manejar el caso en que el producto no exista
            return render(request, 'error.html', {'error_message': 'Producto no encontrado'})
        
    else:
        return render(request, 'error.html', {'error_message': 'Metodo no permitido'})

@login_required
def NewEditedProduct(request):
    try:
        if request.method == 'POST':
            form = EditProductForm(request.POST, request.FILES)
            if form.is_valid():
                # Guardar el formulario para obtener el nuevo producto
                new_product = form.save()

                # Obtener el product_id desde el formulario
                product_id = request.POST.get('product_id')
                
                try:
                    # Obtener el producto antiguo
                    old_product = Products.objects.get(pk=product_id)

                    # vendedor del usuario actual
                    vendedor = Vendedores.objects.get(usuarioVendedor=request.user.username)

                    #añadir nuevo producto
                    #vendedor.productos.add(new_product)

                    # Desvincular el antiguo producto del vendedor
                    vendedor.productos.remove(product_id)

                    # Eliminar el producto antiguo si ya no está asociado a ningún vendedor
                    # if .count() == 0:
                    #   old_product.delete()
                except Products.DoesNotExist:
                    pass  # Manejar la excepción si el producto antiguo no existe

                # Guardar el nuevo producto
                new_product.save()

                return redirect('editar_productos')
        else:
            return HttpResponse("Método no válido, se debe especificar el producto")

    except Exception as e:
        return HttpResponse(f"Error: {str(e)}")
    
def pago(request):
    return render(request, 'pago.html')

def efectivo(request):
    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()  # Obtener datos del carrito

    # Calcular el total del carrito sumando los precios acumulados de todos los productos
    total_carrito = sum(item_data['acumulado'] for item_data in carrito_data.values())

    return render(request, 'efectivo.html', {'carrito_data': carrito_data, 'total_carrito': total_carrito})

def nequi(request):

    carrito = Carrito(request)
    carrito_data = carrito.obtener_carrito()

    total_por_vendedor = {}

     # Inicializa una lista para almacenar los QR de los vendedores
    vendedores = set()

    # Itera sobre los elementos del carrito para obtener los IDs de los vendedores
    for item in carrito_data.values():
        vendedor_id = item.get('vendedor_id')
        total_acumulado = item.get('acumulado')
        vendedor = Vendedores.objects.get(id=vendedor_id)
        vendedores.add(vendedor)
        total_por_vendedor[vendedor] = total_acumulado

    return render(request, 'nequi.html', {"total_por_vendedor" : total_por_vendedor})

def registroValidador(request):
    if request.method == 'GET':
        return render(request, 'registroValidador.html', {
            # utiliza la instancia del formulario personalizado
            'register': RegistroValidadorForm()
        })
    else:
        form = RegistroValidadorForm(request.POST)
        if form.is_valid():

            nombre=form.cleaned_data['first_name']
            apellido=form.cleaned_data['last_name']
            correo=form.cleaned_data['email']

            try:
                # Código para enviar el correo electrónico
                subject = 'Solicitud de ' + nombre + apellido + ' para validador Agroweb'
                message = '''
                <html>
                <head></head>
                <body>
                    <h2>Solicitud de validador</h2>
                    <p>Buenos dias,</p>
                    <p>Quisiera registrarme en Agroweb con el rol de validador.</p>
                    <p> mi correo es '''+ correo + '''</p> 
                    <p>Espero su respuesta</p>
                </body>
                </html>
                ''' 
                enviar_correos(settings.CORREO, subject, message)

                print("solicitud de validador enviada")
            except:
                print("no se pudo enviar el correo de solicitud validador")

            return redirect('mapa')
        else:
            # Logica para mostrar los errores
            errors_dict = form.errors.as_data()
            email_error = ""

            # Itera sobre los errores del form
            for field, error_list in errors_dict.items():
                for error in error_list:
                    if 'correo' in field:
                        email_error += error.message + ". "

            # Renderiza el formulario con los mensajes de error personalizados
            return render(request, 'registroValidador.html', {"register": form, "email_error": email_error})
        
def landingPago(request):
    try:
        enviar_correos(request.user.email, "Pago en efectivo de tu compra", "<h2>Hola!<h2><br><p>Has escogido pagar por efectivo en tu compra agroweb, por favor dirigete hacia el vendedor de la tienda</p><br><p>Saludos,</p><br><h4>Equipo de Agroweb</h4>")
    except:
        print("no se puede enviar el correo de pago en efectivo")
    return render(request, 'landing_pago.html')