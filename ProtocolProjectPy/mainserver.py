import socket
import threading

import prtcp


HOST = "0.0.0.0"
MAIN_PORT = 5000

MAX_SESSIONS = 10000
sessions = {}

sessions_lock = threading.Lock()

# ============================================================
# Utility
# ============================================================

def print_message(prefix, message):
    print(f"\n[{prefix}]")
    print(message.decode(errors="replace"))

def send_message(sock, message):
    sock.sendall(message.encode())

def recv_message(sock):

    # Recieve exactly one PRTCP message
    # PRTCP messages end with \\r\\n\\r\\n

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
# Canvas Server Registration
# ============================================================

def handle_canvas_registration(sock, address):

    try:
        data = recv_message(sock)

        if data is None:
            return

        print_message(f"Canvas Server {address} -> Main Server", data)

        message = prtcp.parse(data)

        if not isinstance(message, prtcp.RegSession):

            error = prtcp.AnsError(error_code=1)
            send_message(sock, error)

            return

        session_id = message.session
        port = message.port
        canvas_x = message.canvas_x
        canvas_y = message.canvas_y

        with sessions_lock:

            if session_id in sessions:

                print(f"[MAIN] Session {session_id:05d} is already registered.")
                error = prtcp.AnsError(error_code=2)
                send_message(sock, error)

                return

            if len(sessions) >= MAX_SESSIONS:

                error = prtcp.AnsError(error_code=3)

                send_message(sock, error)

                return

            sessions[session_id] = {
                "host": address[0],
                "port": port,
                "canvas_x": canvas_x,
                "canvas_y": canvas_y
            }

        response = prtcp.AckReg()

        print_message(
            "Main Server -> Canvas Server",
            response.encode()
        )

        send_message(sock, response)

        print(
            f"[MAIN] Registered session "
            f"{session_id:05d} on {address[0]}:{port}"
        )

        # Keep this connection alive.
        # If the Canvas Server disconnects, remove its session.

        while True:

            data = recv_message(sock)

            if data is None:
                break

            print_message(
                f"Canvas Server {address} -> Main Server",
                data
            )

    except Exception as e:

        print(
            f"[MAIN] Canvas registration error "
            f"from {address}: {e}"
        )

    finally:

        # Remove any session belonging to this Canvas Server.
        with sessions_lock:

            to_remove = []

            for session_id, info in sessions.items():

                if (
                    info["host"] == address[0]
                    and info["port"] == port
                ):
                    to_remove.append(session_id)

            for session_id in to_remove:

                del sessions[session_id]

                print(
                    f"[MAIN] Removed session "
                    f"{session_id:05d}"
                )

        sock.close()


# ============================================================
# Client
# ============================================================

def handle_client(sock, address):

    try:

        data = recv_message(sock)

        if data is None:
            return

        print_message(
            f"Client {address} -> Main Server",
            data
        )

        message = prtcp.parse(data)

        if not isinstance(message, prtcp.ReqJoin):

            response = prtcp.AnsError(error_code=1)

            print_message(
                "Main Server -> Client",
                response.encode()
            )

            send_message(sock, response)

            return

        requested_session = message.session

        # ----------------------------------------------------
        # SESSION=00000
        # Find any available session
        # ----------------------------------------------------

        with sessions_lock:

            if requested_session == 0:

                if not sessions:

                    response = prtcp.AnsError(error_code=0)

                else:

                    session_id = next(iter(sessions))

                    info = sessions[session_id]

                    response = prtcp.AnsJoin(
                        session=session_id,
                        port=info["port"],
                        canvas_x=info["canvas_x"],
                        canvas_y=info["canvas_y"]
                    )

            # ------------------------------------------------
            # Specific session
            # ------------------------------------------------

            elif requested_session in sessions:

                session_id = requested_session

                info = sessions[session_id]

                response = prtcp.AnsJoin(
                    session=session_id,
                    port=info["port"],
                    canvas_x=info["canvas_x"],
                    canvas_y=info["canvas_y"]
                )

            else:

                response = prtcp.AnsError(error_code=0)

        print_message(
            "Main Server -> Client",
            response.encode()
        )

        send_message(sock, response)

    except Exception as e:

        print(
            f"[MAIN] Client error {address}: {e}"
        )

    finally:
        sock.close()


# ============================================================
# Main
# ============================================================

def main():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, MAIN_PORT))
    server.listen()

    print(
        f"[MAIN] Main Server listening on "
        f"{HOST}:{MAIN_PORT}"
    )

    print(
        "[MAIN] Waiting for Canvas Servers and Clients..."
    )

    while True:

        sock, address = server.accept()

        try:

            data = recv_message(sock)

            if data is None:
                sock.close()
                continue

            print_message(
                f"Incoming connection {address}",
                data
            )

            message = prtcp.parse(data)

            # Canvas Server
            if isinstance(message, prtcp.RegSession):

                def registration_thread():
                    handle_registration_with_first_message(
                        sock,
                        address,
                        data,
                        message
                    )

                threading.Thread(
                    target=registration_thread,
                    daemon=True
                ).start()

            # Client
            else:

                def client_thread():
                    handle_client_with_first_message(
                        sock,
                        address,
                        data,
                        message
                    )

                threading.Thread(
                    target=client_thread,
                    daemon=True
                ).start()

        except Exception as e:

            print(
                f"[MAIN] Failed to identify connection "
                f"{address}: {e}"
            )

            sock.close()


# ============================================================
# First-message handlers
# ============================================================

def handle_registration_with_first_message(
    sock,
    address,
    data,
    message
):

    port = message.port
    session_id = message.session
    canvas_x = message.canvas_x
    canvas_y = message.canvas_y

    try:

        with sessions_lock:

            if session_id in sessions:

                response = prtcp.AnsError(
                    error_code=3
                )

                send_message(sock, response)

                return

            if len(sessions) >= MAX_SESSIONS:

                response = prtcp.AnsError(
                    error_code=4
                )

                send_message(sock, response)

                return

            sessions[session_id] = {
                "host": address[0],
                "port": port,
                "canvas_x": canvas_x,
                "canvas_y": canvas_y
            }

        response = prtcp.AckReg()

        print_message(
            "Main Server -> Canvas Server",
            response.encode()
        )

        send_message(sock, response)

        print(
            f"[MAIN] Registered Canvas Session "
            f"{session_id:05d} "
            f"on {address[0]}:{port}"
        )

        # Keep registration connection alive.

        while True:

            incoming = sock.recv(4096)

            if not incoming:
                break

    except Exception as e:

        print(
            f"[MAIN] Canvas Server error: {e}"
        )

    finally:

        with sessions_lock:

            if session_id in sessions:

                if sessions[session_id]["port"] == port:

                    del sessions[session_id]

                    print(
                        f"[MAIN] Session "
                        f"{session_id:05d} removed"
                    )

        sock.close()


def handle_client_with_first_message(
    sock,
    address,
    data,
    message
):

    try:

        if not isinstance(message, prtcp.ReqJoin):

            response = prtcp.AnsError(
                error_code=1
            )

        else:

            # print("checkpoint 1")

            requested_session = message.session

            with sessions_lock:

                if requested_session == 0:

                    if not sessions:

                        response = prtcp.AnsError(
                            error_code=0
                        )

                    else:

                        session_id = next(iter(sessions))

                        info = sessions[session_id]

                        response = prtcp.AnsJoin(
                            session=session_id,
                            port=info["port"],
                            canvas_x=info["canvas_x"],
                            canvas_y=info["canvas_y"]
                        )

                elif requested_session in sessions:

                    print("checkpoint 2")

                    info = sessions[requested_session]
                    
                    response = prtcp.AnsJoin(
                        session=requested_session,
                        port=info["port"],
                        canvas_x=info["canvas_x"],
                        canvas_y=info["canvas_y"]
                    )

                    print("checkpoint 3")

                else:

                    response = prtcp.AnsError(
                        error_code=0
                    )

        print("checkpoint 4")

        print_message(
            "Main Server -> Client",
            response.encode()
        )

        print("checkpoint 5")

        send_message(sock, response)

    except Exception as e:

        print(
            f"[MAIN] Client error: {e}"
        )

    finally:

        sock.close()


if __name__ == "__main__":
    main()