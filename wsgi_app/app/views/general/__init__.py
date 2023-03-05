import os
from flask import Blueprint, jsonify, current_app, flash, request, render_template
from flask_login import login_required
from flask import send_from_directory
from werkzeug.utils import secure_filename
from wsgi_app.app import db, User, UploadForm, BootswatchForm
from wsgi_app.app.wyl.utils import allowed_file

bp_general = Blueprint("general", __name__, url_prefix="/")
print("BP: General")


@login_required
@bp_general.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return jsonify({'status': 'error', 'message': 'No file uploaded'})
    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
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
