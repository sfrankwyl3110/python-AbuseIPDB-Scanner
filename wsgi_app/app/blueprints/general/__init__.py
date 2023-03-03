import os
from flask import Blueprint, render_template, jsonify, send_from_directory, current_app
import random
from PIL import Image


bp_general = Blueprint("general", __name__, url_prefix="/")

favicon_filename = "favicon.ico"


def generate_favicon():
    global favicon_filename

    size = (32, 32)
    img = Image.new('RGB', size)
    pixels = img.load()
    for i in range(size[0]):
        for j in range(size[1]):
            pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    # Save the image as an ICO file
    if not os.path.exists(os.path.join(os.path.join(current_app.root_path, 'static'), 'favicon.ico')):
        img.save(os.path.join(os.path.join(current_app.root_path, 'static'), 'favicon.ico'))

    """
    else:
        print("existing")
        i = 1
        favicon_filename = 'favicon{}.ico'.format(i)
        while os.path.exists(os.path.join(os.path.join(current_app.root_path, 'static', favicon_filename))):
            i += 1

        img.save(os.path.join(os.path.join(current_app.root_path, 'static', favicon_filename)))
    """


@bp_general.route("/")
def main_index():
    return render_template("index.html")


@bp_general.route('/favicon.ico')
def favicon():
    generate_favicon()
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               "favicon.ico", mimetype='image/png')
