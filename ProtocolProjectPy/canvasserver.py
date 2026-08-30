import socket
import threading
import time

import prtcp

from dataclasses import dataclass

MAIN_HOST = "127.0.0.1"
MAIN_PORT = 5000

HOST = "0.0.0.0"

CANVAS_X = 0
CANVAS_Y = 0

HEARTBEAT_INTERVAL = 10


clients = []
clients_lock = threading.Lock()

@dataclass
class Draw:
    x: int
    y: int
    r: int
    g: int
    b: int
    brush_size: int

prevDraws: list[Draw] = []

# ============================================================
# Utility
# ============================================================

def send_message(sock, message):

    data = message.encode()

    sock.sendall(data)


def print_message(prefix, data):

    print(f"\n[{prefix}]")
    print(data.decode(errors="replace"))


def recv_message(sock):

    buffer = b""

    while True:

        data = sock.recv(4096)

        if not data:
            return None

        buffer += data

        separator = b"\r\n\r\n"

        if separator in buffer:

            end = buffer.index(separator) + len(separator)

            return buffer[:end]


# ============================================================
# Register with Main Server
# ============================================================

def register_with_main(session, port, canvasx, canvasy):

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.connect(
        (MAIN_HOST, MAIN_PORT)
    )

    message = prtcp.RegSession(
        session=session,
        port=port,
        canvas_x=canvasx,
        canvas_y=canvasy
    )

    print_message(
        "Canvas Server -> Main Server",
        message.encode()
    )

    send_message(sock, message)

    data = recv_message(sock)

    if data is None:

        print(
            "[CANVAS] Main Server disconnected."
        )

        return None

    print_message(
        "Main Server -> Canvas Server",
        data
    )

    response = prtcp.parse(data)

    if isinstance(response, prtcp.AckReg):

        print(
            f"[CANVAS] Successfully registered "
            f"session {session:05d}"
        )

        return sock

    if isinstance(response, prtcp.AnsError):

        print(
            f"[CANVAS] Registration failed. "
            f"Error code: {response.error_code}"
        )

        sock.close()

        return None

    return None


# ============================================================
# Broadcast
# ============================================================

def broadcast(message, exclude=None):

    data = message.encode()

    with clients_lock:

        for client in clients.copy():

            if client is exclude:
                continue

            try:

                client.sendall(data)

                print_message(
                    "Canvas Server -> Client",
                    data
                )

            except Exception:

                remove_client(client)


# ============================================================
# Remove client
# ============================================================

def remove_client(sock):

    with clients_lock:

        if sock in clients:

            clients.remove(sock)

            print(
                f"[CANVAS] Client disconnected. "
                f"Clients: {len(clients)}"
            )

    try:
        sock.close()
    except:
        pass

# ============================================================
# Update new client with all previoud draws
# ============================================================

def update_new_client(sock):
    with clients_lock:
        if sock in clients:
            print(f"[CANVAS] Sending {len(prevDraws)} previous draws")

            for draw in prevDraws:
                print(f"[CANVAS] Sending draw: {draw}")
                send_message(
                    sock,
                    prtcp.AnsUpdate(
                        x=draw.x,
                        y=draw.y,
                        r=draw.r,
                        g=draw.g,
                        b=draw.b,
                        brush_size=draw.brush_size
                    )
                )

# ============================================================
# Client handler
# ============================================================

def handle_client(sock, address):

    print(
        f"[CANVAS] Client connected: {address}"
    )

    with clients_lock:
        clients.append(sock)

    update_new_client(sock)

    try:

        while True:

            data = recv_message(sock)

            if data is None:
                break

            print_message(
                f"Client {address} -> Canvas Server",
                data
            )

            try:

                message = prtcp.parse(data)

            except prtcp.PRTCPError as e:

                print(
                    f"[CANVAS] Invalid PRTCP message: {e}"
                )

                error = prtcp.AnsError(
                    error_code=1
                )

                send_message(sock, error)

                continue

            # ------------------------------------------------
            # REQDRAW
            # ------------------------------------------------

            if isinstance(message, prtcp.ReqDraw):

                # Check coordinates against canvas

                if (
                    message.x < 0
                    or message.x > CANVAS_X
                    or message.y < 0
                    or message.y > CANVAS_Y
                ):

                    error = prtcp.AnsError(
                        error_code=4
                    )

                    send_message(sock, error)

                    continue

                # Application-level drawing would happen here.
                #
                # For this prototype we only print it.

                print(
                    f"[CANVAS] DRAW "
                    f"({message.x}, {message.y}) "
                    f"RGB=({message.r}, "
                    f"{message.g}, "
                    f"{message.b}) "
                    f"SIZE={message.brush_size}"
                )

                # Broadcast update to everyone else

                update = prtcp.AnsUpdate(
                    x=message.x,
                    y=message.y,
                    r=message.r,
                    g=message.g,
                    b=message.b,
                    brush_size=message.brush_size
                )

                broadcast(
                    update,
                    exclude=sock
                )

                # Save new Draw to list
                newDraw = Draw(
                    message.x,
                    message.y,
                    message.r,
                    message.g,
                    message.b,
                    message.brush_size
                )
                prevDraws.append(newDraw)

            # ------------------------------------------------
            # REQLEAVE
            # ------------------------------------------------

            elif isinstance(message, prtcp.ReqLeave):

                response = prtcp.AnsLeave()

                print_message(
                    "Canvas Server -> Client",
                    response.encode()
                )

                send_message(sock, response)

                break

            # ------------------------------------------------
            # PING
            # ------------------------------------------------

            elif isinstance(message, prtcp.Ping):

                response = prtcp.Pong()

                print_message(
                    "Canvas Server -> Client",
                    response.encode()
                )

                send_message(sock, response)

            # ------------------------------------------------
            # PONG
            # ------------------------------------------------

            elif isinstance(message, prtcp.Pong):

                print(
                    f"[CANVAS] PONG received from {address}"
                )

            else:

                print(
                    f"[CANVAS] Unexpected message "
                    f"{message.type.value}"
                )

    except Exception as e:

        print(
            f"[CANVAS] Client {address} error: {e}"
        )

    finally:

        remove_client(sock)

        print(
            f"[CANVAS] Connection closed: {address}"
        )


# ============================================================
# Heartbeat
# ============================================================

def heartbeat():

    while True:

        time.sleep(HEARTBEAT_INTERVAL)

        ping = prtcp.Ping()

        with clients_lock:

            for client in clients.copy():

                try:

                    client.sendall(
                        ping.encode()
                    )

                    print_message(
                        "Canvas Server -> Client",
                        ping.encode()
                    )

                except Exception:

                    remove_client(client)


# ============================================================
# Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Ask session number
    # --------------------------------------------------------

    while True:

        try:

            session = int(input("Enter session number (1-10000): "))
            canvasx = int(input("Enter canvas size X (1-9999): "))
            canvasy = int(input("Enter canvas size Y (1-9999): "))

            if (1 <= session <= 10000) and (1 <= canvasx <= 9999) and (1 <= canvasy <= 9999):
                global CANVAS_X
                global CANVAS_Y
                CANVAS_X = canvasx
                CANVAS_Y = canvasy
                break

            print("Session setup input invalid.")

        except ValueError:

            print("Please enter a number.")

    # --------------------------------------------------------
    # Create server socket
    # Port 0 = OS automatically assigns available port
    # --------------------------------------------------------

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        (HOST, 0)
    )

    server.listen()

    actual_port = server.getsockname()[1]

    print(
        f"\n[CANVAS] Canvas Server started"
    )

    print(
        f"[CANVAS] Session : {session:05d}"
    )

    print(
        f"[CANVAS] Port    : {actual_port}"
    )

    print(
        f"[CANVAS] Canvas  : "
        f"{canvasx} x {canvasy}"
    )

    # --------------------------------------------------------
    # Register with Main Server
    # --------------------------------------------------------

    registration_socket = register_with_main(
        session,
        actual_port,
        canvasx,
        canvasy
    )

    if registration_socket is None:

        print(
            "[CANVAS] Could not register with Main Server."
        )

        server.close()

        return

    # --------------------------------------------------------
    # Heartbeat
    # --------------------------------------------------------

    threading.Thread(
        target=heartbeat,
        daemon=True
    ).start()

    # --------------------------------------------------------
    # Accept clients
    # --------------------------------------------------------

    print(
        "\n[CANVAS] Waiting for clients..."
    )

    while True:

        sock, address = server.accept()

        threading.Thread(
            target=handle_client,
            args=(sock, address),
            daemon=True
        ).start()


if __name__ == "__main__":
    main()