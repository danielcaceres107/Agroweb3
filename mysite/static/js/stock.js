var rutapapa = "static/img/papa.jpg"
var rutatomate = "{% static 'img/tomate.jpg' %}"
var imagen = new Image();
imagen.src = rutapapa;
let stockProductos = [
    {id: 1, nombre: "Papa", cantidad: 1, desc: "bulto 60-65kg aprox", precio: 85000, img: papa},
    {id: 2, nombre: "Yuca", cantidad: 1, desc: "bulto 65-70kg aprox", precio: 95000, img: "../../static/img/yuca.jpg"},
    {id: 3, nombre: "Tomate", cantidad: 1, desc: "canasta 50 unidades", precio: 115000, img: rutatomate},
    {id: 4, nombre: "Lechuga", cantidad: 1, desc: "canasta 24 unidades", precio: 30000, img: imagen.src},
    {id: 5, nombre: "Zanahoria", cantidad: 1, desc: "bulto 45kg aprox", precio: 85000, img: '/img/zanahoria.jpg'},
    {id: 6, nombre: "Cebolla", cantidad: 1, desc: "bulto 60-65kg aprox", precio: 155000, img: '/img/cebolla.jpg'},
    {id: 7, nombre: "Aguacate", cantidad: 1, desc: "canasta 10 unidades", precio: 40000, img: '../img/aguacate.jpg' },
    {id: 8, nombre: "Pepino", cantidad: 1, desc: "canasta 20 unidades", precio: 32000, img: 'logo.png' }
]