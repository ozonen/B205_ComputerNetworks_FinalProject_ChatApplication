import logging


# Network configuration

HOST = "127.0.0.1"      # Address the server binds to (localhost by default).
PORT = 5050             # TCP port the server listens on.
BUFFER_SIZE = 4096      # Maximum number of bytes read from the socket at once.
ENCODING = "utf-8"      # Text encoding used for every message.
MSG_END = "\n"          # Every protocol message ends with a newline character.


# Application defaults

# The server always starts with these two rooms so that users have somewhere.

DEFAULT_ROOMS = ["general", "lobby"]



# Logging

def setup_logging(name, log_file):
    """Create and return a simple logger that writes to the console and a file.

    Both the server and the client use this helper so that connections,
    disconnections and errors are all recorded in a consistent format.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Only add handlers once, even if this function is called more than once.
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)

        file_handler = logging.FileHandler(log_file, encoding=ENCODING)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger



# Network helpers

def send_line(sock, text):
    """Send one protocol message over the socket.

    A newline is added to the end so the receiver knows where the message
    stops. This matters because TCP is a byte stream and does not keep the
    message boundaries for us.
    """
    sock.sendall((text + MSG_END).encode(ENCODING))


def recv_lines(sock):
    """Yield complete protocol messages received from the socket.

    Because TCP delivers a continuous stream of bytes, incoming data is
    collected in a buffer and split on newlines so that each value we yield
    is exactly one complete message.
    """
    buffer = ""
    while True:
        data = sock.recv(BUFFER_SIZE)
        if not data:
            break  # An empty result means the other side closed the socket.
        buffer += data.decode(ENCODING)
        while MSG_END in buffer:
            line, buffer = buffer.split(MSG_END, 1)
            line = line.strip()
            if line:
                yield line
