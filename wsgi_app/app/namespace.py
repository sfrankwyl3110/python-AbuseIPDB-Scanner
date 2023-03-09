import base64
import json
from threading import Lock
from flask import session, request
from flask_socketio import Namespace, join_room, rooms, leave_room, close_room, disconnect, emit

thread = None
thread_lock = Lock()


class MyNamespace(Namespace):
    count = 0
    upload_started = False
    upload_finished = False

    def background_thread(self):

        while True:
            self.socketio.sleep(3)
            # self.socketio.emit("my_response", {"data": "data", "count": self.count})
            self.count += 1

    @staticmethod
    def on_my_event(message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']})

    @staticmethod
    def on_my_broadcast_event(message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             broadcast=True)

    @staticmethod
    def on_join(message):
        join_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})

    @staticmethod
    def on_leave(message):
        leave_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})

    @staticmethod
    def on_close_room(message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': 'Room ' + message['room'] + ' is closing.',
              'count': session['receive_count']},
             room=message['room'])
        close_room(message['room'])

    @staticmethod
    def on_my_room_event(message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response',
             {'data': message['data'], 'count': session['receive_count']},
             room=message['room'])

    @staticmethod
    def on_disconnect_request():
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('my_response', {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()

    @staticmethod
    def on_my_ping():
        emit('my_pong')

    def on_upload(self, data):
        if not self.upload_started and not self.upload_finished:
            self.upload_started = True
            self.upload_finished = False
        self.upload_started = False
        self.upload_finished = True
        if isinstance(data, str):
            data = data.encode("utf-8")
        emit('result', {'result': 'success', 'data': json.dumps({"data": base64.b64encode(data).decode("utf-8")})})

    def on_connect(self):
        global thread
        with thread_lock:
            if thread is None:
                thread = self.socketio.start_background_task(self.background_thread)
        emit('my_response', {'data': 'Connected', 'count': 0})

    # noinspection PyUnresolvedReferences
    @staticmethod
    def on_disconnect():
        print('Client disconnected', request.sid)
        emit('my_response', {'data': 'Client disconnected: {}'.format(request.sid), 'count': 0})
