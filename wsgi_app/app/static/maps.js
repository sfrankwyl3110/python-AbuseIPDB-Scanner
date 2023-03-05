let lat
let lng
function initMap_default(local_lat, local_lng) {
    if (parseFloat(local_lat) > 0 || parseFloat(local_lng) > 0) {
        window.localStorage.setItem("map_lat", local_lat)
        window.localStorage.setItem("map_lng", local_lng)
    }
    if (parseFloat(window.localStorage.getItem("map_lat")) > 0 && parseFloat(window.localStorage.getItem("map_lng")) > 0) {
        let local_lat = parseFloat(window.localStorage.getItem("map_lat"));
        let local_lng = parseFloat(window.localStorage.getItem("map_lng"));

    }

        console.log(window.localStorage.getItem("map_lat"))
        // The location of Uluru
        let home = { lat: parseFloat(local_lat), lng: parseFloat(local_lng) };
        // The map, centered at Uluru
        let map = new google.maps.Map(document.getElementById("map"), {
            zoom: 5,
            center: home,
            disableDefaultUI: true,
            zoomControl: false,
          mapTypeControl: true,
          mapTypeControlOptions: {
              style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
              mapTypeIds: ["roadmap", "terrain", "satellite"],
              position: google.maps.ControlPosition.BOTTOM_LEFT,

            },


          scaleControl: true,
          scaleControlOptions: {
            position: google.maps.ControlPosition.BOTTOM_LEFT,
          },
          streetViewControl: false,
          rotateControl: false,
          fullscreenControl: true,
          fullscreenControlOptions: {
            position: google.maps.ControlPosition.BOTTOM_LEFT,
          }

        });
        // The marker, positioned at Uluru
        let marker = new google.maps.Marker({
            position: new google.maps.LatLng(home.lat, home.lng),
            map: map,
        });
        $(marker).on('click', (function (marker) {
            return function () {
                infowindow.setContent("State: ${e['state']}<br>County: ${e['location']}<br>Address: ${e['address']}");
                infowindow.open(map, marker);
            }
        })(marker));

    return map

}
function initMap(data) {
    if (typeof  data !== 'undefined' && data.length  > 0) {

    var center = {lat: data[0]['latitude'], lon: data[0]['longitude']};
    var map = new google.maps.Map(document.getElementById('map'), {
        zoom: 4,
        center: center
    });

    var infowindow =  new google.maps.InfoWindow({});
    var marker;

    data.forEach(e => {
        marker = new google.maps.Marker({
                position: new google.maps.LatLng(e['latitude'], e['longitude']),
                map: map,
                title: e['address'],
        });
        google.maps.event.addListener(marker, 'click', (function (marker) {
            return function () {
                infowindow.setContent("State: ${e['state']}<br>County: ${e['location']}<br>Address: ${e['address']}");
                infowindow.open(map, marker);
            }
        })(marker));
    });

    }
}
