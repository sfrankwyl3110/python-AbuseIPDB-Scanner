import csv
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from wsgi_app.app import current_config


proxy_source_fields = ["url", "css_selector"]


class ProxyChains:

    config_path = None
    source_path = None

    def __init__(self):
        self.source_path = os.path.join(current_config.PROJECT_LOCATION, 'app', 'proxy_data', 'proxies_ok.csv')
        self.config_path = os.path.join(
            os.path.dirname(self.source_path), "proxychains-{}.conf".format(
                datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
        )
        super().__init__()

    def generate_config(self, output_file, proxy_input_csv=None):
        if proxy_input_csv is None:
            proxy_input_csv = os.path.join(current_config.PROJECT_LOCATION, 'app', 'proxy_data', 'proxies_ok.csv')

        existing_proxies = {}
        if os.path.isfile(output_file):
            with open(output_file, 'r') as f:
                for line in f:
                    try:
                        protocol, ip, port = line.strip().split(' ')
                        existing_proxies[f'{ip}:{port}'] = protocol
                    except ValueError:
                        pass
        with open(proxy_input_csv) as f, open(output_file, 'w') as out:
            reader = csv.DictReader(f)
            for row in reader:
                ip_port = row['ip_port']
                ip, port = ip_port.split(':')
                protocol = row['protocol']
                if ip_port in existing_proxies and existing_proxies[ip_port] != protocol:
                    print(f'Updating protocol for {ip_port} to {protocol}')
                out.write(f'{protocol} {ip} {port}\n')
        print(f'Config file saved to {output_file}')

    def scrape_source_rows(self, proxy_source_url, css_selector="section#list table tr"):
        return BeautifulSoup(
            requests.get(proxy_source_url).content, 'html.parser'
        ).select(css_selector)

    def add_proxy_source(
            self,
            current_proxy_source_url,
            current_selector,
            proxysource_target_filepath=os.path.join(
                current_config.PROJECT_LOCATION, 'app', 'proxy_data', "proxy_sources.csv")
    ):
        global proxy_source_fields

        with open(proxysource_target_filepath, "w", encoding="utf-8", newline='') as current_css_selector_file:
            current_writer = csv.DictWriter(current_css_selector_file, fieldnames=proxy_source_fields)
            current_writer.writeheader()
            current_writer.writerow({
                "url": current_proxy_source_url,
                "css_selector": current_selector
            })
            current_css_selector_file.close()

    def check_csv_row(self, csv_filepath, field, value_expected):
        row_exists = False
        with open(csv_filepath, 'r') as proxy_source_file:
            csv_reader = csv.DictReader(proxy_source_file)

            for row in csv_reader:
                if row[field] == value_expected:
                    row_exists = True
                    break
            proxy_source_file.close()
        return row_exists
