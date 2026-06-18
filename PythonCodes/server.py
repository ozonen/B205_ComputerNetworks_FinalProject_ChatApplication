import argparse
import socket
import threading
import config

clients = {}              # username -> socket
rooms = {}                # room name -> set of member usernames
active = {}               # username -> the room the user is currently talking in
lock = threading.Lock()   # guards the three dictionaries above

log = config.setup_logging("server", "server.log")


def broadcast(room, text, exclude=None):
    """Send a message to every member of a room.
    """
    for username in list(rooms.get(room, [])):
        if username == exclude:
            continue
        sock = clients.get(username)
        if sock is not None:
            try:
                config.send_line(sock, text)
            except OSError:
                pass  # The client has gone; its own thread will clean up.


def register(sock, lines):
    """Read NICK messages until the client picks a valid username.

    Returns the accepted username, or None if the client disconnected first.
    """
    for line in lines:
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0].upper() == "NICK":
            name = parts[1].strip()
            with lock:
                if not name or " " in name:
                    config.send_line(sock, "ERROR Username cannot be empty or contain spaces.")
                elif name in clients:
                    config.send_line(sock, "ERROR That username is already taken.")
                else:
                    home = config.DEFAULT_ROOMS[0]
                    clients[name] = sock
                    rooms[home].add(name)
                    active[name] = home
                    config.send_line(sock, "OK Welcome %s! You are in room '%s'." % (name, home))
                    return name
        else:
            config.send_line(sock, "ERROR Please register first with: NICK <name>")
    return None


def create_room(username, name):
    """Create a brand new room and switch the creator into it."""
    sock = clients[username]
    if not name or " " in name:
        config.send_line(sock, "ERROR Room name cannot be empty or contain spaces.")
    elif name in rooms:
        config.send_line(sock, "ERROR Room '%s' already exists." % name)
    else:
        rooms[name] = {username}
        active[username] = name
        config.send_line(sock, "OK Created and joined room '%s'." % name)
        log.info("%s created room '%s'", username, name)


def join_room(username, name):
    """Join an existing room and make it the active room."""
    sock = clients[username]
    if name not in rooms:
        config.send_line(sock, "ERROR Room '%s' does not exist. Use CREATE to make it." % name)
    else:
        rooms[name].add(username)
        active[username] = name
        config.send_line(sock, "OK Joined room '%s'." % name)
        broadcast(name, "INFO %s joined the room." % username, exclude=username)


def switch_room(username, name):
    """Switch the active room to one the user has already joined."""
    sock = clients[username]
    if name not in rooms:
        config.send_line(sock, "ERROR Room '%s' does not exist." % name)
    elif username not in rooms[name]:
        config.send_line(sock, "ERROR You are not a member of '%s'. Use JOIN first." % name)
    else:
        active[username] = name
        config.send_line(sock, "OK Now talking in '%s'." % name)


def invite_user(username, argument):
    """Invite another online user into a room (INVITE <user> <room>)."""
    sock = clients[username]
    parts = argument.split(" ", 1)
    if len(parts) != 2:
        config.send_line(sock, "ERROR Usage: INVITE <user> <room>")
        return
    target, room = parts[0].strip(), parts[1].strip()
    if room not in rooms:
        config.send_line(sock, "ERROR Room '%s' does not exist." % room)
    elif target not in clients:
        config.send_line(sock, "ERROR User '%s' is not online." % target)
    else:
        rooms[room].add(target)
        config.send_line(sock, "OK Invited %s to '%s'." % (target, room))
        config.send_line(clients[target],
                         "INFO %s invited you to '%s'. Type /switch %s to talk there."
                         % (username, room, room))
        log.info("%s invited %s to '%s'", username, target, room)


def handle_command(username, line):
    """Parse and act on a single message from a client.

    Returns False when the user wants to quit, otherwise True.
    """
    parts = line.split(" ", 1)
    command = parts[0].upper()
    argument = parts[1].strip() if len(parts) > 1 else ""

    with lock:
        sock = clients[username]
        if command == "MSG":
            room = active[username]
            broadcast(room, "MSG %s %s %s" % (room, username, argument))
        elif command == "CREATE":
            create_room(username, argument)
        elif command == "JOIN":
            join_room(username, argument)
        elif command == "SWITCH":
            switch_room(username, argument)
        elif command == "INVITE":
            invite_user(username, argument)
        elif command == "ROOMS":
            config.send_line(sock, "INFO Rooms: " + ", ".join(sorted(rooms)))
        elif command == "USERS":
            room = active[username]
            config.send_line(sock, "INFO Users in '%s': %s" % (room, ", ".join(sorted(rooms[room]))))
        elif command == "QUIT":
            config.send_line(sock, "INFO Goodbye!")
            return False
        else:
            config.send_line(sock, "ERROR Unknown command: %s" % command)
    return True


def disconnect(username, addr):
    """Remove a user from every room and tell the others they have left."""
    with lock:
        if username and username in clients:
            member_rooms = [r for r, members in rooms.items() if username in members]
            for room in member_rooms:
                rooms[room].discard(username)
            del clients[username]
            active.pop(username, None)
            log.info("%s disconnected", username)
            for room in member_rooms:
                broadcast(room, "INFO %s has left the chat." % username)
    log.info("Connection closed for %s", addr)


def handle_client(sock, addr):
    """Handle one client connection from start to finish."""
    log.info("New connection from %s", addr)
    username = None
    lines = config.recv_lines(sock)  # one generator reused for the whole session
    try:
        username = register(sock, lines)
        if not username:
            return
        log.info("%s registered from %s", username, addr)
        with lock:
            broadcast(active[username], "INFO %s joined the room." % username, exclude=username)
            config.send_line(sock, "INFO Type /help to see the available commands.")
        for line in lines:
            if not handle_command(username, line):
                break
    except OSError as exc:
        log.warning("Connection error for %s: %s", username or addr, exc)
    finally:
        disconnect(username, addr)
        sock.close()


def start_server(host, port):
    """Set up the listening socket and accept clients forever."""
    for room in config.DEFAULT_ROOMS:
        rooms[room] = set()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen()
    log.info("Server listening on %s:%s", host, port)

    try:
        while True:
            client_sock, addr = server_sock.accept()
            thread = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        log.info("Server shutting down (keyboard interrupt).")
    finally:
        server_sock.close()


def main():
    parser = argparse.ArgumentParser(description="Multi-room TCP chat server.")
    parser.add_argument("--host", default=config.HOST, help="Address to bind to.")
    parser.add_argument("--port", type=int, default=config.PORT, help="Port to listen on.")
    args = parser.parse_args()
    start_server(args.host, args.port)


if __name__ == "__main__":
    main()
