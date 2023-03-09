from flask import Blueprint, render_template
from flask_login import login_required

bp_audio = Blueprint("audio", __name__)


@login_required
@bp_audio.route('/audio')
def audio_index():
    return render_template('audio.html')
