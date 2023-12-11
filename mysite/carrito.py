class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        carrito = self.session.get("carrito")
        if not carrito:
            self.session["carrito"] = {}
            self.carrito = self.session["carrito"]
        else:
            self.carrito = carrito

    def agregar(self, producto, vendedor_id, tienda):
        id = str(vendedor_id) + str(producto.pk)
        if id not in self.carrito.keys():
            self.carrito[id]={
                "producto_id": producto.pk,
                "nombre": producto.nombreProd,
                "acumulado": int(producto.precioProd),
                "cantidad": 1,
                "vendedor_id": vendedor_id,
                "tienda": tienda, 
                "last_product_id": producto.pk,
                "last_vendedor_id": vendedor_id
            }
        else:
            self.carrito[id]["cantidad"] += 1
            if "acumulado" in self.carrito[id]:
                self.carrito[id]["acumulado"] += int(producto.precioProd)
            else:
                self.carrito[id]["acumulado"] = int(producto.precioProd)
        self.guardar_carrito()

    def guardar_carrito(self):
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def eliminar(self, producto, vendedor_id):
        id = str(vendedor_id) + str(producto.pk)
        if id in self.carrito:
            del self.carrito[id]
            self.guardar_carrito()

    def restar(self, producto, vendedor_id):
        id = str(vendedor_id) + str(producto.pk)
        if id in self.carrito.keys():
            self.carrito[id]["cantidad"] -= 1
            self.carrito[id]["acumulado"] -= int(producto.precioProd)
            if self.carrito[id]["cantidad"] <= 0:
                self.eliminar(producto, vendedor_id)
            self.guardar_carrito()

    def limpiar(self):
        self.session["carrito"] = {}
        self.session.modified = True

    def obtener_carrito(self):
        return self.carrito