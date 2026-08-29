import socket
import threading

import prtcp


MAIN_HOST = "127.0.0.1"
MAIN_PORT = 5000


# ============================================================
# Utility
# ============================================================

def print_message(prefix, data):

    message_type = data.split(b"\r\n", 1)[0].decode()

    if message_type in ("PING", "PONG"):
        return

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


def send_message(sock, message):

    data = message.encode()

    print_message(
        "Client -> Server",
        data
    )

    sock.sendall(data)


# ============================================================
# Server receiver
# ============================================================

def receive_loop(sock):

    while True:

        try:

            data = recv_message(sock)

            if data is None:

                print(
                    "\n[CLIENT] Server disconnected."
                )

                break

            print_message(
                "Server -> Client",
                data
            )

            try:

                message = prtcp.parse(data)

            except prtcp.PRTCPError as e:

                print(
                    f"[CLIENT] Invalid message: {e}"
                )

                continue

            # ------------------------------------------------
            # ANSUPDATE
            # ------------------------------------------------

            if isinstance(message, prtcp.AnsUpdate):

                print(
                    "\n"
                    f"[UPDATE] "
                    f"X={message.x} "
                    f"Y={message.y} "
                    f"RGB=({message.r}, "
                    f"{message.g}, "
                    f"{message.b}) "
                    f"BSIZE={message.brush_size}"
                )

            # ------------------------------------------------
            # ANSERROR
            # ------------------------------------------------

            elif isinstance(message, prtcp.AnsError):

                print(
                    f"\n[ERROR] "
                    f"ERRCODE={message.error_code}"
                )

                if message.error_code == 0:

                    print(
                        "[ERROR] "
                        "The requested session is not available."
                    )

            # ------------------------------------------------
            # PING
            # ------------------------------------------------

            elif isinstance(message, prtcp.Ping):

                pong = prtcp.Pong()

                send_message(
                    sock,
                    pong
                )

            # ------------------------------------------------
            # ANSLEAVE
            # ------------------------------------------------

            elif isinstance(message, prtcp.AnsLeave):

                print(
                    "\n[CLIENT] Successfully left session."
                )

                break

        except Exception as e:

            print(
                f"\n[CLIENT] Receive error: {e}"
            )

            break


# ============================================================
# Join Main Server
# ============================================================

def join_session(session):

    main_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print(
        f"[CLIENT] Connecting to Main Server "
        f"{MAIN_HOST}:{MAIN_PORT}"
    )

    main_sock.connect(
        (MAIN_HOST, MAIN_PORT)
    )

    request = prtcp.ReqJoin(
        session=session
    )

    send_message(
        main_sock,
        request
    )

    data = recv_message(main_sock)

    if data is None:

        print(
            "[CLIENT] Main Server disconnected."
        )

        main_sock.close()

        return None

    print_message(
        "Main Server -> Client",
        data
    )

    response = prtcp.parse(data)

    main_sock.close()

    if isinstance(response, prtcp.AnsError):

        if response.error_code == 0:

            print(
                "[CLIENT] "
                "The requested session is not available."
            )

        else:

            print(
                f"[CLIENT] Main Server error "
                f"code {response.error_code}"
            )

        return None

    if not isinstance(response, prtcp.AnsJoin):

        print(
            "[CLIENT] Unexpected response from Main Server."
        )

        return None

    print(
        f"\n[CLIENT] Joined session "
        f"{response.session:05d}"
    )

    print(
        f"[CLIENT] Canvas Server port: "
        f"{response.port}"
    )

    print(
        f"[CLIENT] Canvas size: "
        f"{response.canvas_x} x "
        f"{response.canvas_y}"
    )

    # Return information needed to connect
    return response


# ============================================================
# Drawing input
# ============================================================

def drawing_loop(sock):

    print(
        "\nEnter drawing commands:"
    )

    print(
        "  x y r g b bsize"
    )

    print(
        "Example:"
    )

    print(
        "  100 200 255 0 0 5"
    )

    print(
        "Type 'leave' to leave the canvas."
    )

    while True:

        try:

            command = input("\ndraw> ").strip()

        except EOFError:

            command = "leave"

        if command.lower() == "leave":

            message = prtcp.ReqLeave()

            send_message(
                sock,
                message
            )

            break

        values = command.split()

        if len(values) != 6:

            print(
                "Format: x y r g b bsize"
            )

            continue

        try:

            x = int(values[0])
            y = int(values[1])
            r = int(values[2])
            g = int(values[3])
            b = int(values[4])
            bsize = int(values[5])

        except ValueError:

            print(
                "All values must be integers."
            )

            continue

        if not (
            0 <= r <= 255
            and 0 <= g <= 255
            and 0 <= b <= 255
        ):

            print(
                "RGB must be between 0 and 255."
            )

            continue

        if not 0 <= bsize <= 9:

            print(
                "BSIZE must be between 0 and 9."
            )

            continue

        message = prtcp.ReqDraw(
            x=x,
            y=y,
            r=r,
            g=g,
            b=b,
            brush_size=bsize
        )

        try:

            send_message(
                sock,
                message
            )

        except Exception as e:

            print(
                f"[CLIENT] Failed to send draw: {e}"
            )

            break


# ============================================================
# Main
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "       PRTCP Paint Client"
    )

    print(
        "================================"
    )

    while True:

        try:

            session = int(
                input(
                    "Enter session number "
                    "(0 = any available): "
                )
            )

            if 0 <= session <= 10000:
                break

            print(
                "Session must be 0-10000."
            )

        except ValueError:

            print(
                "Please enter a number."
            )

    # --------------------------------------------------------
    # Contact Main Server
    # --------------------------------------------------------

    join_response = join_session(session)

    if join_response is None:

        return

    # --------------------------------------------------------
    # Connect directly to Canvas Server
    # --------------------------------------------------------

    canvas_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    print(
        f"\n[CLIENT] Connecting to Canvas Server..."
    )

    canvas_sock.connect(
        (
            MAIN_HOST,
            join_response.port
        )
    )

    print(
        f"[CLIENT] Connected to session "
        f"{join_response.session:05d}"
    )

    # --------------------------------------------------------
    # Receiver thread
    # --------------------------------------------------------

    receiver = threading.Thread(
        target=receive_loop,
        args=(canvas_sock,),
        daemon=True
    )

    receiver.start()

    # --------------------------------------------------------
    # Input loop
    # --------------------------------------------------------

    drawing_loop(canvas_sock)

    canvas_sock.close()

    print(
        "[CLIENT] Client terminated."
    )


if __name__ == "__main__":
    main()