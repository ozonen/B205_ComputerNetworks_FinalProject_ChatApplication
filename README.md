# B205 - Computer Networks - ChatApp


####  - Ozgur Onen - GH1044899
#### - Bora Gürses - GH1034408


ChatApp is a lightweight, real-time group chat application written in
Python. It uses a classic **client–server architecture** over **TCP sockets**
and **threading** to support many users talking in multiple chat rooms at the
same time from the terminal, without a GUI and no third-party libraries.

This project was built for the **B205 Computer Networks** module to demonstrate
socket programming, a custom application-layer protocol, concurrency with
threads, configuration management and basic logging.


## Features

- **Client–server model** built on TCP sockets.
- **Concurrent users** — every client is handled in its own thread, so 3+ users
  can chat simultaneously.
- **Unique usernames** — each user picks a name when they connect; duplicates
  are rejected.
- **Multiple chat rooms** — the server starts with two rooms (`general` and
  `lobby`). Users can:
  - **create** new rooms,
  - **join** existing rooms,
  - **switch** between rooms they have joined, and
  - **invite** other online users into a room.
- **Room isolation** — a message is only delivered to members of the room it
  was sent in.
- **Configuration management** — all settings live in `config.py` and can be
  overridden at run time with command-line arguments.
- **Error handling & logging** — connections, disconnections, room actions and
  errors are written to the console and to a log file.


## Project Structure

| File         | Responsibility                                                        |
|--------------|-----------------------------------------------------------------------|
| `config.py`  | Shared settings (host, port, etc.) and network helper functions.      |
| `server.py`  | The chat server: accepts clients, manages rooms, routes messages.     |
| `client.py`  | The terminal client: sends user input and prints incoming messages.   |

Two log files (`server.log` and `client.log`) are created automatically when
the programs run.


## Requirements

- **Python 3.8 or newer**.
- No external packages — only the Python standard library
  (`socket`, `threading`, `json`, `argparse`, `logging`).

Check your Python version:

```bash
python --version
```

## Installation

No installation step is needed beyond having Python. Simply download or clone
the ".py" files into one folder.



## Configuration

The default settings are defined at the top of `config.py`:

```python
HOST = "127.0.0.1"   # address the server binds to
PORT = 5050          # TCP port
BUFFER_SIZE = 4096   # bytes read per recv() call
ENCODING = "utf-8"   # text encoding
DEFAULT_ROOMS = ["general", "lobby"]
```

You can either **edit these values directly**, or **override the host and port
at run time** using command-line arguments (see below). Command-line arguments
take priority over the defaults.


## Running the Application

### 1. Start the server

Open a terminal and run:

```bash
python server.py
```

To use a different address or port:

```bash
python server.py --host 0.0.0.0 --port 6000
```

You should see:

```
2026-06-18 22:10:01 [INFO] Server listening on 127.0.0.1:5050
```

> `--host 0.0.0.0` makes the server reachable from other machines on the
> network. When connecting from another computer, the clients must use the
> server machine's IP address.

### 2. Start one or more clients

Open a **separate terminal window for each user** and run:

```bash
python client.py
```

Connect to a server on another host/port:

```bash
python client.py --host 192.168.1.20 --port 6000
```

Skip the username prompt by passing it directly:

```bash
python client.py --username alice
```

When a client starts it asks for a username, prints the command help, and you
can begin chatting.


## In-Chat Commands

Anything you type that does **not** start with `/` is sent as a message to your
current room. The slash commands are:

| Command                   | Description                                         |
|---------------------------|-----------------------------------------------------|
| `/create <room>`          | Create a new room and switch to it.                 |
| `/join <room>`            | Join an existing room (and switch to it).           |
| `/switch <room>`          | Switch to a room you have already joined.           |
| `/invite <user> <room>`   | Invite an online user into a room.                  |
| `/rooms`                  | List every room on the server.                      |
| `/users`                  | List the users in your current room.                |
| `/help`                   | Show the command help.                              |
| `/quit`                   | Leave the chat and close the client.                |


## Example Session

**Terminal 1 — server**

```text
$ python server.py
2026-06-18 22:10:01 [INFO] Server listening on 127.0.0.1:5050
2026-06-18 22:10:09 [INFO] ozgur registered from ('127.0.0.1', 50512)
2026-06-18 22:10:14 [INFO] bora registered from ('127.0.0.1', 50513)
2026-06-18 22:10:25 [INFO] ozgur created room 'project'
2026-06-18 22:10:31 [INFO] ozgur invited bora to 'project'
```

**Terminal 2 — Ozgur**

```text
$ python client.py --username ozgur
* Welcome ozgur! You are in room 'general'.
[general] ozgur: hi
/create project
* Created and joined room 'project'.
/invite bora project
* Invited bora to 'project'.
[project] ozgur: bora, check this!
[project] bora: nice bro!
```

**Terminal 3 — Bora**

```text
$ python client.py --username bora
* Welcome bora! You are in room 'general'.
* ozgur invited you to 'project'. Type /switch project to talk there.
/switch project
* Now talking in 'project'.
[project] ozgur: bora, check this!
[project] bora: nice bro!
```


## How It Works (Quick Overview)

- The **server** binds a TCP socket, listens for connections, and starts a new
  **thread per client**. Shared state (the connected users and the rooms) is
  stored in dictionaries protected by a `threading.Lock`.
- Communication uses a simple **newline-delimited text protocol**. Clients send
  commands such as `NICK ozgur`, `MSG hello`, `CREATE project` or
  `INVITE bora project`. The server replies with tagged lines such as
  `OK ...`, `ERROR ...`, `INFO ...` or `MSG <room> <user> <text>`.
- Each **client** runs two threads: one reads keyboard input and sends it to the
  server, while the other listens for incoming messages and prints them, so
  messages appear in real time.

A full explanation of the architecture and protocol is in project report.


## Logging

Both programs log to the console and to a file:

- `server.log` — server start-up, client connections/disconnections, room
  actions and errors.
- `client.log` — connection and shutdown events for that client.


## Troubleshooting

| Problem                               | Likely cause / fix                                              |
|---------------------------------------|-----------------------------------------------------------------|
| Could not connect to ...              | The server is not running, or the host/port is wrong.           |
| `[Errno 98]/[WinError 10048]` address in use | The port is busy — wait a moment or pick another `--port`. |
|`That username is already taken.       | Choose a different username; names must be unique.              |
| Client window seems "stuck"           | It is waiting for input — just type a message and press Enter.  |

Stop the **server** or a **client** at any time with `Ctrl + C` (or `/quit` in
the client).


## Limitations & Possible Improvements

- Messages are sent in plain text (no encryption / TLS).
- Usernames exist only while connected — there are no persistent accounts.
- Chat history is not stored; new users only see messages sent after they join.

These were intentional scope decisions to keep the project small and focused on
the networking concepts.

