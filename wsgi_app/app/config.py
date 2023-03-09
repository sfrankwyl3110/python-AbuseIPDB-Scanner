import logging
import os.path


class BaseConfig:
    FORMATTER = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s',
        datefmt='%d.%m.%Y %H:%M:%S'
    )

    async_mode = "gevent"
    target_foldername = "target"
    source_foldername = "uploads"
    logs_foldername = "logs"
    sessions_foldername = "sessions"

    TESSERACT_CMD = ""
    SECRET_KEY = 'secret!'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.join(os.path.dirname(os.path.abspath(__file__)))), "uploads")
    allowed_extensions = ['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']
    MAX_CONTENT_LENGTH = 1024 * 1000 * 1000
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DB_HOST = "localhost"
    DB_USER = "pdf_manager"
    DB_PASS = "pdf_password"
    DB_NAME = "pdf_manager"

    # set default button style and size, will be overwritten by macro parameters
    BOOTSTRAP_BTN_STYLE = 'primary'
    BOOTSTRAP_BTN_SIZE = 'sm'

    # set default icon title of table actions
    BOOTSTRAP_TABLE_VIEW_TITLE = 'Read'
    BOOTSTRAP_TABLE_EDIT_TITLE = 'Update'
    BOOTSTRAP_TABLE_DELETE_TITLE = 'Remove'
    BOOTSTRAP_TABLE_NEW_TITLE = 'Create'
    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
    PROJECT_LOCATION = None


class WindowsConfig(BaseConfig):
    static_url_path = "/static"
    UPLOAD_FOLDER = r"D:\repos\python-AbuseIPDBScanner\wsgi_app\app\uploads"
    SQLALCHEMY_DATABASE_URI = None
    PROJECT_LOCATION = r'D:\repos\python-AbuseIPDBScanner\wsgi_app'
    logs_foldername = "logs"
    sessions_foldername = "sessions"

    socketio_cors_allowed = [
        "http://127.0.0.1:5000",
        "http://localhost:5005",
        "http://localhost:5000",
        "http://192.168.137.69:5055",
        "http://localhost:5055"
    ]

    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    DB_PORT = 3316

    def __init__(self):
        super().__init__()


class ProductionConfig(BaseConfig):
    static_url_path = "/pdf/static"
    UPLOAD_FOLDER = "/usr/test/python-PDFManager/app_1/app/uploads"
    socketio_cors_allowed = ["https://9teeth.wyl-online.de"]

    def __init__(self):
        super().__init__()
