import argparse
import os
import socket
import threading

import config

log = config.setup_logging("client", "client.log")

HELP_TEXT = """
Available commands:
  /create <room>          Create a new room and switch to it
  /join <room>            Join an existing room
  /switch <room>          Switch to a room you have already joined
  /invite <user> <room>   Invite an online user into a room
  /rooms                  List all rooms on the server
  /users                  List the users in your current room
  /help                   Show this help text
  /quit                   Leave the chat
Anything else you type is sent as a message to your current room.
"""


def format_message(line):
    """Turn a raw protocol line from the server into readable text."""
    parts = line.split(" ", 1)
    tag = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    if tag == "MSG":
        # Format on the wire is:  MSG <room> <user> <text>
        bits = rest.split(" ", 2)
        if len(bits) == 3:
            room, user, text = bits
            return "[%s] %s: %s" % (room, user, text)
        return rest
    elif tag == "ERROR":
        return "[!] " + rest
    elif tag in ("INFO", "OK"):
        return "* " + rest
    return line


def build_message(text):
    """Translate what the user typed into a protocol message for the server.

    Returns None if the input was handled locally (for example /help).
    """
    if not text.startswith("/"):
        return "MSG " + text

    parts = text[1:].split(" ", 1)
    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else ""

    if command == "help":
        print(HELP_TEXT)
        return None

    # Map the slash commands to the protocol commands the server expects.
    mapping = {
        "create": "CREATE", "join": "JOIN", "switch": "SWITCH",
        "invite": "INVITE", "rooms": "ROOMS", "users": "USERS", "quit": "QUIT",
    }
    if command not in mapping:
        print("Unknown command. Type /help to see the list.")
        return None

    protocol_command = mapping[command]
    return protocol_command if not argument else protocol_command + " " + argument


def receive_messages(lines):
    """print every message that arrives from the server."""
    try:
        for line in lines:
            print(format_message(line))
    except OSError:
        pass
    # If we get here the connection has dropped, so stop the whole program.
    print("\nDisconnected from the server.")
    os._exit(0)


def register(sock, lines, username):
    """Keep sending NICK until the server accepts a username. Returns it."""
    while True:
        if not username:
            username = input("Choose a username: ").strip()
        config.send_line(sock, "NICK " + username)
        try:
            reply = next(lines)
        except StopIteration:
            print("Server closed the connection.")
            return None
        print(format_message(reply))
        if reply.startswith("OK"):
            return username
        username = None  # if the name was rejected.


def main():
    parser = argparse.ArgumentParser(description="Terminal chat client.")
    parser.add_argument("--host", default=config.HOST, help="Server address.")
    parser.add_argument("--port", type=int, default=config.PORT, help="Server port.")
    parser.add_argument("--username", default=None, help="Username (optional).")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((args.host, args.port))
    except OSError as exc:
        print("Could not connect to %s:%s (%s)" % (args.host, args.port, exc))
        return
    log.info("Connected to %s:%s", args.host, args.port)

    # The same line generator is used for registration and then handed to the
    # listener thread, so no buffered bytes are ever lost.
    lines = config.recv_lines(sock)
    username = register(sock, lines, args.username)
    if not username:
        sock.close()
        return

    print(HELP_TEXT)
    threading.Thread(target=receive_messages, args=(lines,), daemon=True).start()

    # Main loop: read user input and send it to the server.
    try:
        while True:
            text = input()
            if not text:
                continue
            message = build_message(text)
            if message is None:
                continue  # A local-only command such as /help was handled.
            config.send_line(sock, message)
            if message == "QUIT":
                break
    except (KeyboardInterrupt, EOFError):
        try:
            config.send_line(sock, "QUIT")
        except OSError:
            pass
    finally:
        sock.close()
        log.info("Client closed.")


if __name__ == "__main__":
    main()
