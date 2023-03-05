from flask import Blueprint, render_template, current_app, jsonify
from flask_login import login_required
from app.wyl.maps import request_coordinates

from wsgi_app.app import process_data

bp_maps = Blueprint("maps", __name__)


@login_required
@bp_maps.route('/maps2')
def maps2_index():
    lat, lng = request_coordinates()
    return render_template('map_2.html', api_key=current_app.config['maps_api_key'], lat=lat, lng=lng)


@login_required
@bp_maps.route('/maps')
def maps_index():
    return render_template('map.html', api_key=current_app.config['maps_api_key'])


@login_required
@bp_maps.route('/displaylocations')
def displaylocations():  # Obtain the CSV data.
    location: dict = process_data()  # Forward the data to the source that called this API.
    return jsonify(location)
