import base64
import csv
import json
import os
import platform
from io import BytesIO
from PIL import PngImagePlugin
from wsgi_app.app.config import ProductionConfig, WindowsConfig, BaseConfig

is_win = platform.platform().lower().startswith("win")
if is_win:
    current_config = WindowsConfig
else:
    current_config = ProductionConfig


def create_missing_directories(config_object: BaseConfig):
    base_dir = current_config.PROJECT_LOCATION if os.path.isdir(
        current_config.PROJECT_LOCATION) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    logs_directory = os.path.join(base_dir, config_object.logs_foldername)
    sessions_directory = os.path.join(base_dir, config_object.sessions_foldername)
    os.makedirs(logs_directory, exist_ok=True)
    os.makedirs(sessions_directory, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_config.allowed_extensions


def clean_dict(d):
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = clean_dict(v)
        try:
            json.dumps(v)
            cleaned[k] = v
        except (TypeError, OverflowError):
            if isinstance(v, PngImagePlugin.PngImageFile):
                buffer = BytesIO()
                v.save(buffer, format='PNG')
                cleaned[k] = base64.b64encode(buffer.getvalue()).decode("utf-8")
            else:
                cleaned[k] = str(v)
    return cleaned


def search_lang(lang):
    if len(lang) == 3:
        target_ = '639-1'
        source_ = '639-2'
    else:
        target_ = '639-2'
        source_ = '639-1'

    if os.path.isfile(os.path.join(current_config.PROJECT_LOCATION, "app", "static", "iso_639.csv")):
        with open(os.path.join(current_config.PROJECT_LOCATION, "app", "static", "iso_639.csv"),
                  encoding="utf-8") as csv_f:
            csv_reader = csv.DictReader(csv_f)
            next(csv_reader)

            for entry in csv_reader:
                if entry.get(source_) == lang:
                    csv_f.close()
                    return entry.get(target_)

            csv_f.close()
    return False
