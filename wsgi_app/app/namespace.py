from threading import Lock
from flask import session, request
from flask_socketio import Namespace, join_room, rooms, leave_room, close_room, disconnect

thread = None
thread_lock = Lock()


class MyNamespace(Namespace):
    count = 0

    def background_thread(self):

        while True:
            self.socketio.sleep(3)
            self.socketio.emit("my_response", {"data": "data", "count": self.count})
            self.count += 1

    def on_my_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': message['data'], 'count': session['receive_count']})

    def on_my_broadcast_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': message['data'], 'count': session['receive_count']},
                           broadcast=True)

    def on_join(self, message):
        join_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': 'In rooms: ' + ', '.join(rooms()),
                            'count': session['receive_count']})

    def on_leave(self, message):
        leave_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': 'In rooms: ' + ', '.join(rooms()),
                            'count': session['receive_count']})

    def on_close_room(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                                           'count': session['receive_count']},
                           room=message['room'])
        close_room(message['room'])

    def on_my_room_event(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': message['data'], 'count': session['receive_count']},
                           room=message['room'])

    def on_disconnect_request(self):
        session['receive_count'] = session.get('receive_count', 0) + 1
        self.socketio.emit('my_response',
                           {'data': 'Disconnected!', 'count': session['receive_count']})
        disconnect()

    def on_my_ping(self):
        self.socketio.emit('my_pong')
    upload_started = False
    upload_finished = False

    def on_upload(self, data):
        if not self.upload_started and not self.upload_finished:
            self.upload_started = True
            self.upload_finished = False
            print("uploading")
            print(
                data
            )
        self.upload_started = False
        self.upload_finished = True
        self.socketio.emit('result', {'result': 'success'})

    def on_connect(self):
        global thread
        with thread_lock:
            if thread is None:
                thread = self.socketio.start_background_task(self.background_thread)
        self.socketio.emit('my_response', {'data': 'Connected', 'count': 0})

    def on_disconnect(self):
        print('Client disconnected', request.sid)
        self.socketio.emit('my_response', {'data': 'Client disconnected: {}'.format(request.sid), 'count': 0})
