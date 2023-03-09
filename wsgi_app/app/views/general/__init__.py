import inspect
import json
import os
import threading
import time
import uuid
from flask import Blueprint, jsonify, current_app, flash, request, render_template, session
from flask_login import login_required, current_user
from flask import send_from_directory
from werkzeug.utils import secure_filename
from wsgi_app.app import db, User, UploadForm, BootswatchForm
from wsgi_app.app.wyl.utils import allowed_file
from wsgi_app.app.wyl.pdf import extract_values

bp_general = Blueprint("general", __name__, url_prefix="/")


class ExtractionThread(threading.Thread):
    started = False
    started_t = 0
    results = {}

    def __init__(self, current_uuid):
        self.current_uuid = current_uuid
        super().__init__()

    def run(self) -> None:
        self.started_t = time.time()
        self.started = True
        self.results = extract_values(self.current_uuid)


e_thread = None


@login_required
@bp_general.route('/run_extraction')
def run_extraction():
    global e_thread
    ret = False
    results = {}

    if e_thread is None:

        if "extraction_uuid" not in session.keys():
            session["extraction_uuid"] = str(uuid.uuid4())
        current_uuid = session["extraction_uuid"]

        e_thread = ExtractionThread(current_uuid)
        e_thread.daemon = True
        e_thread.start()
    else:
        if e_thread.is_alive():
            print("still running")
            ret = False
        else:
            results = e_thread.results
    current_uuid = session["extraction_uuid"]
    return jsonify({"success": ret, "uuid": current_uuid, "results": results})


@login_required
@bp_general.route('/get_files')
def get_files_():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    bp_root = os.path.dirname(current_dir)
    uploads_path = current_app.config.get('UPLOAD_FOLDER')
    excluded = ["count", "index"]
    files = {}
    for file in os.listdir(os.path.join(os.path.dirname(bp_root), os.path.basename(uploads_path))):
        if file.endswith('.pdf'):
            json_path = os.path.join(os.path.dirname(bp_root), os.path.basename(uploads_path), file.rstrip(".pdf")+".json")

            if file not in files.keys():
                stat_ = os.stat(os.path.join(os.path.dirname(bp_root), os.path.basename(uploads_path), file))
                file_stat_dict = {}
                for m in inspect.getmembers(stat_):
                    if not m[0].startswith("_") and m[0] not in excluded:
                        file_stat_dict[m[0]] = m[1]
                if os.path.isfile(json_path):
                    json_data = open(json_path).read()
                    file_stat_dict["upload_details"] = json.loads(json_data)
                files[file] = file_stat_dict
    return jsonify({"files": files})


@login_required
@bp_general.route('/upload', methods=['POST'])
def upload_file():
    email = current_user.email
    print("current_uploader: {}".format(email))
    if 'file' not in request.files:
        flash('No file part')
        return jsonify({'status': 'error', 'message': 'No file uploaded'})
    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        with open(os.path.join(current_app.config['UPLOAD_FOLDER'], filename).rstrip(".pdf")+".json", "w") as json_f:
            json_f.write(json.dumps({
                "uploaded": time.time(),
                "uploader": email
            }))
            json_f.close()

        return jsonify({'status': 'success', 'message': 'File uploaded successfully'})
    else:
        return jsonify({'status': 'error', 'message': 'extension Not allowed'})


@login_required
@bp_general.route('/user/delete')
def delete_user_account():
    users = User.query.all()
    for user in users:
        print(user.username)

    users = User.query.filter_by(username='izzy3110').all()
    if len(users) == 0:
        ret = False
    else:
        for user in users:
            db.session.delete(user)
        db.session.commit()
        ret = True
    return jsonify({"success": ret})


@login_required
@bp_general.route('/upload_file')
def upload_index():
    form = UploadForm()
    return render_template('upload.html', form=form)


@login_required
@bp_general.route('/get_uploaded_files')
def uploaded_files_index():
    files = []
    for f in os.listdir(current_app.config["UPLOAD_FOLDER"]):
        if f.endswith(".pdf"):
            files.append(f)
    return jsonify({"folder": current_app.config["UPLOAD_FOLDER"], "contents": files})


@login_required
@bp_general.route('/bootswatch', methods=['GET', 'POST'])
def test_bootswatch():
    form = BootswatchForm()
    if form.validate_on_submit():
        if form.theme_name.data == 'default':
            current_app.config['BOOTSTRAP_BOOTSWATCH_THEME'] = None
        else:
            current_app.config['BOOTSTRAP_BOOTSWATCH_THEME'] = form.theme_name.data
        flash(f'Render style has been set to {form.theme_name.data}.')
    else:
        if current_app.config['BOOTSTRAP_BOOTSWATCH_THEME'] is not None:
            form.theme_name.data = current_app.config['BOOTSTRAP_BOOTSWATCH_THEME']
    return render_template('bootswatch.html', form=form)


@login_required
@bp_general.route('/delete_uploaded', methods=["POST"])
def delete_uploaded_file():
    ret = False
    file_ = request.form.get('file')
    if request.method == "POST" and "confirmed" in request.form.keys():
        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], file_))
        exists_ = os.path.isfile(os.path.join(current_app.config["UPLOAD_FOLDER"], file_))
        ret = True if not exists_ else False
        return jsonify(
            {"success": ret, "args": str(request.args), "form": str(request.form.keys()), "exists_": exists_})

    exists_ = os.path.isfile(os.path.join(current_app.config["UPLOAD_FOLDER"], file_))
    return jsonify({"success": ret, "args": str(request.args), "form": str(request.form.keys()),
                    "exists_": exists_})


@bp_general.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
