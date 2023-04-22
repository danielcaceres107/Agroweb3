let map;

function initMap() {
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat:4.564055528477374, lng: -73.99200191926067 },
    zoom: 8
  });
  // NOTE: This uses cross-domain XHR, and may not work on older browsers.
  //map.data.loadGeoJson("simple.geojson");
}

window.initMap = initMap;