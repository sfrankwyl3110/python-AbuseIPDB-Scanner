import logging

from flask import Flask
from flask_socketio import SocketIO
from app import create_app

# Set the log level to DEBUG to increase verbosity
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('socketio').setLevel(logging.DEBUG)
logging.getLogger('engineio').setLevel(logging.DEBUG)


app: Flask = create_app()
    
if __name__ == '__main__':
    socketio: SocketIO = app.config.get('socketio')
    socketio.run(app=app, host="localhost", port=5005, debug=True)
