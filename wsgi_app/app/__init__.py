import base64
import logging
import os
import platform
from datetime import datetime
import googlemaps
import onetimepass
import pyotp
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, current_app
from flask_assets import Environment, Bundle
from flask_bootstrap import Bootstrap5
from flask_cors import CORS
from flask_login import UserMixin, login_required
from flask_login import current_user, LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from wsgi_app.app.forms import BootswatchForm, TokenForm, RegisterForm, LoginForm
from wsgi_app.app.namespace import MyNamespace
from wsgi_app.app.wyl import process_data
from wsgi_app.app.forms import UploadForm
from wsgi_app.app.wyl.maps import request_coordinates
from wsgi_app.app.wyl.pdf import PDFManager
from wsgi_app.app.wyl.utils import search_lang
from wsgi_app.app.config import WindowsConfig, BaseConfig

is_win = platform.platform().lower().startswith("win")
if is_win:
    current_config = WindowsConfig
else:
    current_config = config.ProductionConfig

load_dotenv(".env")

totp = pyotp.TOTP(os.environ.get('TOTP_SECRET'))

async_mode = WindowsConfig.async_mode

db = SQLAlchemy()
lm = LoginManager()
bootstrap = Bootstrap5()
cors = CORS()
oauth = OAuth()

socketio = SocketIO(async_mode=async_mode, cors_allowed_origins=WindowsConfig.socketio_cors_allowed)

pdf_manager: PDFManager = PDFManager()

# log level to DEBUG
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)


def create_app():
    global socketio, pdf_manager, oauth, db

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
        static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
        static_url_path=WindowsConfig.static_url_path
    )
    app.config.from_object(WindowsConfig)
    app.config.__setattr__('_conf', WindowsConfig)
    app.config["MAPS_ENABLED"] = False

    assets = Environment(app)

    assets.url = app.static_url_path
    assets.register('main',
                    'css/src/style.css', 'css/src/layout.css',
                    output='cached.css', filters='cssmin')
    assets.register('scss_responsive', Bundle(
        'css/src/responsive.scss',
        filters='pyscss',
        output='responsive.css'
    ))

    upload_folder = WindowsConfig.UPLOAD_FOLDER
    if not os.path.isdir(upload_folder):
        os.mkdir(upload_folder)

    oauth = OAuth(app)
    bootstrap.init_app(app)

    lm.init_app(app)
    cors.init_app(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(
        WindowsConfig.DB_USER,
        os.environ.get('DB_PASS', WindowsConfig.DB_PASS),
        WindowsConfig.DB_HOST,
        WindowsConfig.DB_PORT,
        WindowsConfig.DB_NAME
    )

    print(app.config['SQLALCHEMY_DATABASE_URI'])

    db.init_app(app)
    app.config["db"] = db

    if app.config["MAPS_ENABLED"]:
        app.config['maps_api_key'] = os.environ.get('GOOGLE_MAPS_API_KEY', None)
        if app.config['maps_api_key'] is not None:
            app.config['gmaps'] = googlemaps.Client(key=app.config['maps_api_key'])
        else:
            app.config['gmaps'] = False

    # Views
    # GENERAL
    # /
    # /login
    from wsgi_app.app.views.general import bp_general as general_view
    app.register_blueprint(general_view)

    # AUTH
    # /toggle_2fa
    # /register
    # /google
    from wsgi_app.app.views.auth import bp_auth as auth_view
    app.register_blueprint(auth_view)

    # AUDIO
    # /audio
    from wsgi_app.app.views.audio import bp_audio as audio_view
    app.register_blueprint(audio_view)

    # --------------------------------------------------

    @lm.user_loader
    def load_user(user_id):
        return User.query.filter_by(id=user_id).first()

    @lm.request_loader
    def load_user_from_request(current_request):
        api_key = current_request.args.get('api_key')
        if api_key:
            user = User.query.filter_by(api_key=api_key).first()
            if user:
                return user

        api_key = current_request.headers.get('Authorization')
        if api_key:
            api_key = api_key.replace('Basic ', '', 1)
            try:
                api_key = base64.b64decode(api_key)
            except TypeError:
                pass
            user = User.query.filter_by(api_key=api_key).first()
            if user:
                return user
        return None

    @login_required
    @app.post('/run')
    def run_manager():
        global pdf_manager
        running = False
        if pdf_manager is not None:
            pdf_manager.run()
            running = True
            return jsonify({"success": True, "running": running,
                            "target": pdf_manager.target_folder if pdf_manager.target_folder is not None else "",
                            "source": pdf_manager.source_folder if pdf_manager.source_folder is not None else ""
                            }
                           )
        else:
            pdf_manager = PDFManager(current_socketio=current_app.config.get('socketio'))
            return jsonify({"success": False, "running": running,
                            "target": pdf_manager.target_folder if pdf_manager.target_folder is not None else "",
                            "source": pdf_manager.source_folder if pdf_manager.source_folder is not None else ""
                            }
                           )

    @app.route('/')
    def index():
        authenticated = current_user.is_authenticated
        is_login = True if request.args.get('login') is not None else False
        form = LoginForm()
        upload_form = UploadForm()
        kwargs = {
            "template_name_or_list": "index.html",
            "pdf_manager": pdf_manager,
            "is_authenticated": authenticated,
            "form": form,
            "is_login": is_login,
            "async_mode": async_mode,
            "app_settings_2fa_enabled": current_app.config.get("2fa_enabled"),
            "upload_template_html": render_template("upload_embed.html", form=upload_form)
        }
        if authenticated:
            kwargs.update({
                "user": current_user
            })

        return render_template(**kwargs)

    socketio.on_namespace(MyNamespace('/'))

    with app.app_context():
        if "IS_RESET" in os.environ.keys():
            print("RESET: {}".format(os.environ.get("IS_RESET")))
            db.drop_all()
        db.create_all()
    socketio.init_app(app)
    if pdf_manager is not None:
        pdf_manager = PDFManager(current_socketio=socketio)

    oauth.init_app(app)

    from wsgi_app.app.views.proxy import bp_proxy
    app.register_blueprint(bp_proxy)

    app.config["socketio"] = socketio
    return app


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    create_time = db.Column(db.String(100), nullable=False)


class APIRequest(db.Model):
    __tablename__ = 'api_requests'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    create_time = db.Column(db.Integer, nullable=False, unique=True)


class User(UserMixin, db.Model):
    """User model."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    email = db.Column(db.String(128), unique=True)
    secondary_emails = db.Column(db.Text())
    two_factor_enabled = db.Column(db.Boolean())
    profile_pic = db.Column(db.Text())
    password_hash = db.Column(db.String(128))
    otp_secret = db.Column(db.String(16))
    create_time = db.Column(db.Numeric(precision=10, asdecimal=False, decimal_return_scale=None))
    locale = db.Column(db.String(3))
    name = db.Column(db.String(32))

    two_factor_enabled_default = False

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.create_time = int(datetime.now().timestamp()) \
            if "create_time" not in kwargs.keys() else kwargs["create_time"]
        self.two_factor_enabled = self.two_factor_enabled_default \
            if "two_factor_enabled" not in kwargs.keys() else kwargs["two_factor_enabled"]
        if self.otp_secret is None:
            # generate a random secret
            self.otp_secret = base64.b32encode(os.urandom(10)).decode('utf-8')

    def toggle_two_factor_enabled(self):
        if self.two_factor_enabled:
            self.two_factor_enabled = False
        else:
            self.two_factor_enabled = True
        db.session.commit()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_totp_uri(self):
        return 'otpauth://totp/' + self.username + '@2FA-Demo?secret={0}&issuer=2FA-Demo' \
            .format(self.otp_secret)

    def verify_totp(self, token):
        return onetimepass.valid_totp(token, self.otp_secret)


class APIKeys(UserMixin, db.Model):
    """User model."""
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column("user_id", db.ForeignKey(User.id), primary_key=True)
    api_key = db.Column(db.String(255), unique=True)


class UploadedFiles(UserMixin, db.Model):
    """User model."""
    __tablename__ = 'uploaded_files'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column("user_id", db.ForeignKey(User.id))
    filename = db.Column(db.String(255))
    create_time = db.Column(db.Integer, nullable=False)
    hash = db.Column(db.Text())
    filesize = db.Column(db.String(255))
