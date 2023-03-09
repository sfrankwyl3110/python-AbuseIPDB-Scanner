import logging
import os
import time
import pyqrcode
from datetime import datetime
from io import BytesIO
from flask import Blueprint, url_for, redirect, flash, session, render_template, abort, jsonify, request, \
    current_app
from flask_login import current_user, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy

from wsgi_app.app import RegisterForm, User, current_config, oauth, TokenForm, Message, LoginForm


bp_auth = Blueprint('auth', __name__, url_prefix="/")


@bp_auth.route('/login', methods=['GET', 'POST'], strict_slashes=False)
def login():
    logging.debug("method: {}".format(request.method))
    form = LoginForm()
    session["remember"] = form.remember.data
    app_db = current_app.config["db"]
    if current_user.is_authenticated:
        print("is authenticated")
        return redirect(url_for('index'))

    else:
        logging.debug("session_keys: {}".format(",".join(session.keys())))
        user = app_db.session.query(User).filter_by(username=form.username.data).first()
        users = app_db.session.query(User).all()
        logging.debug(form.username.data)

        form_found_user = False
        for user in users:
            if user.username == form.username.data:
                form_found_user = True

        if form_found_user:
            logging.debug("found USER")
            # print(form.password.data)
            # print(user.create_time)
            session["username"] = user.username
            login_user(user)
            if user.password_hash is None:
                if user.email.endswith("googlemail.com"):
                    logging.debug("is a google")
                    return redirect(url_for('google', ref="login"))
            else:
                if "google_email" in session.keys():
                    google_user = User.query.filter_by(email=session["google_email"]).first()
                    if google_user is not None:
                        login_user(google_user, remember=True)
                        if google_user.two_factor_enabled:
                            if not google_user.verify_totp(form.token.data):
                                flash('2fa enabled: Invalid username, password or token.')
                                login_user(google_user)
                                del session["google_email"]
                                del session["ref"]

                                return redirect("/pdf" + url_for('enter_token'))
                        else:
                            session["username"] = google_user.username
                            session["login_t"] = time.time()
                            del session["google_email"]
                        return redirect("/pdf" + url_for('index'))

            if not user.verify_password(form.password.data):
                print('Invalid username, password.')
                flash('Invalid username, password.')
                return redirect("/pdf" + url_for('index', login=True))
            if user.two_factor_enabled:
                if not user.verify_password(form.password.data) or \
                        not user.verify_totp(form.token.data):
                    flash('2fa enabled: Invalid username, password or token.')
                    login_user(user)
                    return redirect("/pdf" + url_for('enter_token'))
            login_user(user)
            text_message = "User-Login: {}".format(user.username)
            message = Message(text=text_message, author=user.username, category="SYS",
                              create_time=datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
            current_app.config["db"].session.add(message)
            current_app.config["db"].session.commit()

            flash('You are now logged in!')
            return redirect(url_for('index'))

    return render_template("login.html", form=form)


@bp_auth.route('/register', methods=['GET', 'POST'], endpoint='pdf_register', strict_slashes=False)
def register():
    print(url_for('auth.pdf_register'))
    """User registration route."""
    if current_user.is_authenticated:
        # if user is logged in we get out of here
        return redirect("/pdf" + url_for('index'))
    form = RegisterForm()
    user = User.query.filter_by(username=form.username.data).first()

    if user is not None:
        flash('Username already exists.')
        return redirect("/pdf" + url_for('pdf_register'))
    app_db = current_app.config["db"]
    email = app_db.session.query(User).filter_by(email=form.email.data).first()
    if email is not None:
        flash('email already exists.')
        return redirect("/pdf" + url_for('pdf_register'))

    if form.validate_on_submit():
        # add new user to the database

        user = User(username=form.username.data, password=form.password.data, email=form.email.data)
        current_app.config.get["db"].session.add(user)
        current_app.config.get["db"].session.commit()

        # redirect to the two-factor auth page, passing username in session
        session['username'] = user.username
        login_user(user)
        return redirect("/pdf" + url_for('index'))
    else:
        print("not validated")
    return render_template('register.html', form=form)


@bp_auth.route('/toggle_2fa', methods=["GET", "POST"], strict_slashes=False)
def togge_2fa():
    if request.method == "POST":
        if current_user.is_authenticated:
            current_user.toggle_two_factor_enabled()
            return jsonify({"enabled": current_user.two_factor_enabled})
    else:
        if current_user.is_authenticated:
            if current_user.two_factor_enabled is None:
                current_user.two_factor_enabled = True
            return jsonify({"enabled": current_user.two_factor_enabled})
        else:
            return jsonify({"success": False, "message": "no login"})


@bp_auth.route('/logout', strict_slashes=False)
def logout():
    """User logout route."""
    logout_user()
    if "username" in session.keys():
        del session["username"]
    if "google_email" in session.keys():
        del session["google_email"]
    return redirect(url_for('index'))


@bp_auth.route('/twofactor', endpoint='pdf_twofactor', strict_slashes=False)
def two_factor_setup():
    if 'username' not in session:
        return redirect(url_for('index'))
    app_db = current_app.config["db"]
    user = app_db.session.query(User).filter_by(username=session['username']).first()
    if user is None:
        return redirect(url_for('pdf_register'))
    # since this page contains the sensitive qrcode, make sure the browser
    # does not cache it
    return render_template('two-factor-setup.html'), 200, {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'}


@bp_auth.route('/qrcode', strict_slashes=False)
def qrcode():
    if 'username' not in session:
        abort(404)
    app_db = current_app.config["db"]
    user = app_db.session.query(User).query.filter_by(username=session['username']).first()
    if user is None:
        abort(404)

    # for added security, remove username from session
    del session['username']

    # render qrcode for FreeTOTP
    url = pyqrcode.create(user.get_totp_uri())
    stream = BytesIO()
    url.svg(stream, scale=3)
    return stream.getvalue(), 200, {
        'Content-Type': 'image/svg+xml',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'}


@bp_auth.route('/google', strict_slashes=False)
def google():
    print(request.args.get('ref'))

    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", None)
    google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", None)
    google_discovery_url = (
        current_config.GOOGLE_DISCOVERY_URL
    )

    if request.args.get('ref') is not None:
        if request.args.get('ref') == "login":
            session["ref"] = "login"
    oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url=google_discovery_url,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    redirect_uri = url_for('auth.google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp_auth.route('/google/auth/', strict_slashes=False)
def google_auth():
    token = oauth.google.authorize_access_token()
    print(token)
    google_user = oauth.google.parse_id_token(token, None)
    print(" Google User ", google_user)
    session["google_user"] = google_user
    session["google_email"] = google_user.get('email')
    app_db = current_app.config["db"]
    user = app_db.session.query(User).query.filter_by(email=session["google_email"]).first()

    if user is not None:
        print("USER")
        print(user)
        print(user.create_time)
        user.profile_pic = google_user.get('picture')
        current_app.get["db"].session.commit()
        login_user(user)
    url_target = "auth.register_google"
    if "ref" in session.keys():
        ref = session["ref"]
        if ref == "login":
            url_target = "auth.login"
    return redirect(url_for(url_target))


@bp_auth.route('/register_google', methods=["GET", "POST"], strict_slashes=False)
def register_google():
    form = RegisterForm()
    if "google_email" in session.keys():
        form.email.data = session["google_email"]
    if request.method == "POST":
        if not form.validate_on_submit():
            temp_form = form
            temp_form.__delattr__('password')
            temp_form.__delattr__('password_again')
            # print("valid: " + str(temp_form.validate_on_submit()))

            if form.validate_on_submit():

                user = User.query.filter_by(username=form.username.data).first()
                if user is not None:
                    flash('Username already exists.')
                    return redirect(url_for('auth.register'))
                # print("GOOGLE USER")
                country_code = "eng"
                google_user = {}
                if "google_user" in session.keys():
                    google_user: dict = session.get('google_user')
                    print(google_user.get('picture'))
                    print(google_user.get('name'))
                    country_code = "eng"
                    if google_user.get('locale') == "de":
                        country_code = "deu"

                # add new user to the database
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    locale=country_code,
                    name=google_user.get('name') if google_user is not None else "",
                    profile_pic=google_user.get('picture') if google_user is not None else ""
                )
                current_app.config.get["db"].session.add(user)
                current_app.config.get["db"].session.commit()

                # redirect to the two-factor auth page, passing username in session
                session['username'] = user.username
                return redirect(url_for('auth.two_factor_setup'))
        else:
            app_db = current_app.config["db"]
            user = app_db.session.query(User).query.filter_by(username=form.username.data).first()
            if user is not None:
                flash('Username already exists.')
                return redirect(url_for('auth.register'))
            # add new user to the database
            user = User(username=form.username.data, email=form.email.data)
            current_app.config.get["db"].session.add(user)
            current_app.config.get["db"].session.commit()

            # redirect to the two-factor auth page, passing username in session
            session['username'] = user.username
            return redirect(url_for('auth.two_factor_setup'))

        return render_template("register.html", form=temp_form, readonly="readonly", disabled="disabled",
                               no_password=True, is_google=True)
    else:
        return render_template("register.html", form=form, readonly="readonly", disabled="disabled",
                               no_password=True, is_google=True)


@bp_auth.route('/try_2fa', methods=['POST'], strict_slashes=False)
def try_2fa():
    ret = False
    form = TokenForm()
    app_db = current_app.config["db"]
    user = app_db.session.query(User).query.filter_by(username=form.username.data).first()
    if user is not None:
        verified = user.verify_totp(form.token.data)
        if not verified:
            return url_for('enter_token')
        else:
            session["username"] = form.username.data
            login_user(user, remember=session["remember"])
            ret = True

    return jsonify({"success": ret})


@bp_auth.route('/enter_token', methods=["GET", "POST"], endpoint='pdf_enter_token', strict_slashes=False)
def enter_token():
    form = TokenForm()
    session_username = session["username"] if ("username" in session.keys()) else False
    if current_user.is_authenticated and not session_username:
        form.username.data = current_user.username
    else:
        if not isinstance(session_username, bool):
            form.username.data = session_username
    return render_template('enter_token.html', form=form)
