import logging
import os.path
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from wsgi_app.app import config, current_config


bp_proxy = Blueprint("proxy", __name__, url_prefix="/proxy")


logs_dir_location = os.path.join(current_config.PROJECT_LOCATION, "app", "logs")

log_filepath = os.path.join(logs_dir_location, "proxy.log")

logger = logging.getLogger(__name__)
handler = logging.FileHandler(log_filepath, mode="a", encoding="utf-8")
handler.mkdir = True
formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(filename)s - %(levelname)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')

handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

# Get the script filename without the .py extension
script_filename = os.path.splitext(os.path.basename(__file__))[0]

proxy_source_filepath = os.path.join(current_config.PROJECT_LOCATION, "app", "proxy_data", "proxy_sources.txt")


@login_required
@bp_proxy.route("/")
def proxy_index():
    return render_template("proxy.html")


@login_required
@bp_proxy.route("/scrape", methods=["POST"])
def proxy_scrape():
    # URL of the website to scrape
    proxy_source_url = request.form.get("url", "https://www.sslproxies.org/")
    css_selector = request.form.get("css_selector", "section#list table tr")
    logger.debug("PROXY: css selektor: {}: {}".format(proxy_source_url, css_selector))
    return jsonify({"success": True})
