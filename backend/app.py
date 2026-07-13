from backend.sockets.collab_socket import socketio
from backend import create_app

create_app_instance = create_app()

if __name__ == "__main__":
    socketio.run(create_app_instance, host="127.0.0.1", port=5001, debug=True)