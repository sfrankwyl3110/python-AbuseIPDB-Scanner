import csv
import json
import logging
import os.path
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from wsgi_app.app import current_config
from wsgi_app.app.wyl.proxy import test_proxy_url


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


class TestThread(threading.Thread):
    running = True
    started = False
    started_t = 0
    processed = 0

    def __init__(self, proxy_url_list):
        if len(proxy_url_list) > 0:
            self.proxy_url_list = proxy_url_list
        super().__init__()
    proxies_working = []
    current_proxy_url = ""

    def run(self) -> None:
        self.started_t = time.time()
        if not self.started:
            self.started = True
        for proxy_url in self.proxy_url_list:
            logger.debug(" PROXY_TEST: testing proxy-url: {}".format(proxy_url))
            self.current_proxy_url = proxy_url
            working = test_proxy_url(proxy_url)
            if working:
                self.proxies_working.append(proxy_url)
            self.processed += 1
            time.sleep(.3)


test_thread: TestThread = TestThread([])


@login_required
@bp_proxy.route("/scrape_test_running", methods=["GET"])
def scrape_test_check_testing():
    global test_thread
    if test_thread is not None:
        current_thread: TestThread = test_thread
        return jsonify({
            "running": current_thread.is_alive(),
            "all_len": len(current_thread.proxy_url_list),
            "tested": current_thread.processed,
            "working": current_thread.proxies_working
        })
    return jsonify({
       "running": False
   })


@login_required
@bp_proxy.route("/scrape_test", methods=["POST"])
def scrape_test():
    global test_thread
    proxy_url_list = json.loads(request.form.get('proxy_list'))
    if test_thread is None:
        start_allowed = True
    else:
        if test_thread.is_alive():
            return jsonify({
                "success": False,
                "message": "test still running",
                "all_len": len(proxy_url_list),
                "tested": test_thread.processed,
                "working": test_thread.proxies_working
            })
        else:
            print("thread ended - start allowed")
            start_allowed = True

    if start_allowed:
        test_thread = TestThread(proxy_url_list)
        test_thread.daemon = True
        test_thread.start()
    else:
        return jsonify({
            "success": False,
            "message": "test still running"
        })
    return jsonify({
        "success": True,
        "list": proxy_url_list,
        "tested": test_thread.processed,
        "working": test_thread.proxies_working
    })


@login_required
@bp_proxy.route("/scrape", methods=["POST"])
def scrape():
    # URL of the website to scrape
    proxy_source_url = request.form.get("url", "https://www.sslproxies.org/")
    css_selector = request.form.get("css_selector", "section#list table tr")
    logger.debug("PROXY: css selector: {}: {}".format(proxy_source_url, css_selector))
    th_rows = BeautifulSoup(
        requests.get(proxy_source_url).content, 'html.parser'
    ).select(css_selector)

    fieldnames = ['ip_addr', 'port', 'country_code', 'country_name', 'anonymity', 'google', 'https', 'last_checked']

    proxy_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../wsgi_app/app/proxy_data")
    if not os.path.isdir(proxy_dir):
        os.makedirs(proxy_dir, exist_ok=True)

    # Load existing proxies from the CSV file
    existing_proxies = {}
    proxies_csv_file = os.path.join(proxy_dir, 'proxies.csv')
    if os.path.isfile(proxies_csv_file):
        with open(proxies_csv_file, 'r', encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, fieldnames=fieldnames)
            for row in reader:
                existing_proxies[row['ip_addr']] = True

    # Create an empty list to store the new proxy servers
    new_proxies = []

    # Loop through each row in the table and extract the proxy server information
    for row in th_rows:
        columns = row.find_all('td')
        if len(columns) > 0:
            proxy_dict = {}
            for column_i in range(0, len(columns)):
                column = columns[column_i]
                proxy_dict[fieldnames[column_i]] = column.get_text()
            if proxy_dict['ip_addr'] not in existing_proxies:
                new_proxies.append(proxy_dict)
            else:
                logger.debug("skipping: {}".format(proxy_dict["ip_addr"]))

    # Append the new proxy servers to the CSV file
    with open(proxies_csv_file, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        for proxy in new_proxies:
            logger.debug("write: {}".format(proxy))
            writer.writerow(proxy)

    return jsonify({"success": True, "selector": css_selector, "new": new_proxies, "existing_proxies": existing_proxies,
                    "rows": list([str(item) for item in th_rows])})
