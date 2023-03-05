import time
from flask import current_app

gmaps_requests = {}
last_gmap_request = 0


def request_coordinates(coordinate_str='Hohe Mauer 21/1, 88271 Esenhausen, Germany'):
    global last_gmap_request
    lat = 0
    lng = 0
    if int(time.time() - last_gmap_request) > 15:
        last_gmap_request = time.time()
        # Geocoding an address
        geocode_result: dict = current_app.config['gmaps'].geocode(coordinate_str)
        if len(geocode_result) > 0:
            for item_i in range(0, len(geocode_result)):
                item = geocode_result[item_i]
                if isinstance(item, dict):
                    geometry_dict: dict = item.get('geometry')
                    found_geo = True if ("lat" in geometry_dict["location"].keys() and "lng" in geometry_dict[
                        "location"].keys()) else False
                    if found_geo:
                        location_dict: dict = geometry_dict["location"]
                        lat = location_dict.get("lat")
                        lng = location_dict.get("lng")
                        gmaps_requests[str(time.time())] = {
                            "str": coordinate_str,
                            "result": {
                                "lat": lat,
                                "lng": lng
                            }
                        }
                    # print(geometry_dict["bounds"].keys())

        return lat, lng
    return 0, 0
