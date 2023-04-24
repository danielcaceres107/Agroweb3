$(document).ready(function(){
  $.ajax({
      url: "{% url 'mydata'%}",
      method: 'GET',
      success: function (data) {
          console.log(data);
          initMap(data);
      }
  });
});

//crear mapa
function initMap(data) {
  const map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 4.564055528477374, lng: -73.99200191926067},
    zoom: 13
  });
  //crear marcador BD django
  const markers = data?.map((i) => {
    const marker = new google.maps.Marker({
        position: { lat: parseFloat(i.latitude), lng: parseFloat(i.longitude)},
        map: map,
    })
  });
  // NOTE: This uses cross-domain XHR, and may not work on older browsers.
  map.data.loadGeoJson("../../static/js/map.geojson");

  // Obtener la ubicacion del usuario
  navigator.geolocation.getCurrentPosition(function(position) {
  var userLocation = {
    lat: position.coords.latitude,
    lng: position.coords.longitude
  };

  //agregar marcador
  var marker = new google.maps.Marker({
      position:userLocation,
      map:map,
      title: 'tu ubicacion',
      icon: '../../static/img/usuario.png'
    });
  });

}

window.initMap = initMap;