import logging

from flask import Flask
from flask_socketio import SocketIO
from wsgi_app.app import create_app

# Set the log level to DEBUG to increase verbosity
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)


app: Flask = create_app()
    
if __name__ == '__main__':
    socketio: SocketIO = app.config.get('socketio')
    socketio.run(app=app, host="0.0.0.0", port=5055, debug=True)
