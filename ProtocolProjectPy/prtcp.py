# PRTCP - Paint Real-Time Canvas Protocol

from dataclasses import dataclass # for auto constructor as ChatGPT says
from enum import Enum

# ============================================================
# Constants
# ============================================================

MAX_SESSIONS = 10000

MIN_SESSION_ID = 1
MAX_SESSION_ID = 10000

MAX_PORT = 65535

MAX_CANVAS_X = 9999
MAX_CANVAS_Y = 9999

MAX_COORDINATE = 9999

MAX_BRUSH_SIZE = 9

MAX_RGB = 255

MAX_ERROR_CODE = 9999

# ============================================================
# Exceptions
# ============================================================

class PRTCPError(Exception):
    "Base class for all PRTCP errors."
    pass
class InvalidMessage(PRTCPError):
    "Message format is invalid."
    pass
class MissingField(PRTCPError):
    "Required field is missing."
    pass
class InvalidField(PRTCPError):
    "A field contains an invalid value."
    pass
class InvalidMessageType(PRTCPError):
    "Unknown message type."
    pass

# ============================================================
# Message Types
# ============================================================

class MessageType(Enum):
    REQJOIN = "REQJOIN" # Client request to join a canvas (need canvas session no.)
    ANSJOIN = "ANSJOIN" # Main server send canvas session no. and port

    REQDRAW = "REQDRAW" # Client send the new drawn stuff to session
    ANSUPDATE = "ANSUPDATE" # Session send to every connected clients aside from the REQDRAW sender to update

    REQLEAVE = "REQLEAVE" # Client send request to leave to session
    ANSLEAVE = "ANSLEAVE" # Session acknowledge leave from client

    PING = "PING" # Ping to client to check if client still connect
    PONG = "PONG" # Pong back to session

    ANSERROR = "ANSERROR" # Comes with error message

    REGSESSION = "REGSESSION" # Register session to main
    ACKREG = "ACKREG" # Main acknowledge registered session


# ============================================================
# Base Message
# ============================================================

class Message:
    type: MessageType

    # Encode message to be send via TCP
    def encode(self) -> bytes:
        return serialize(self)

# ============================================================
# Main Server Messages
# ============================================================

@dataclass
class ReqJoin(Message):
    session: int
    type = MessageType.REQJOIN

@dataclass
class AnsJoin(Message):
    session: int
    port: int
    canvas_x: int
    canvas_y: int

    type = MessageType.ANSJOIN


# ============================================================
# Drawing Messages
# ============================================================

@dataclass
class ReqDraw(Message):
    x: int
    y: int
    r: int
    g: int
    b: int
    brush_size: int

    type = MessageType.REQDRAW

@dataclass
class AnsUpdate(Message):
    x: int
    y: int
    r: int
    g: int
    b: int
    brush_size: int

    type = MessageType.ANSUPDATE


# ============================================================
# Leave Messages
# ============================================================

@dataclass
class ReqLeave(Message):
    type = MessageType.REQLEAVE


@dataclass
class AnsLeave(Message):
    type = MessageType.ANSLEAVE

# ============================================================
# Main and Canvas Register Messages
# ============================================================

@dataclass
class RegSession(Message):
    session: int
    port: int
    canvas_x: int
    canvas_y: int

    type = MessageType.REGSESSION


@dataclass
class AckReg(Message):
    type = MessageType.ACKREG


# ============================================================
# Heartbeat Messages
# ============================================================

@dataclass
class Ping(Message):
    type = MessageType.PING


@dataclass
class Pong(Message):
    type = MessageType.PONG


# ============================================================
# Error Messages
# ============================================================

@dataclass
class AnsError(Message):
    error_code: int

    type = MessageType.ANSERROR

# ========================================================================================================================
# Serialize
# ========================================================================================================================

# ============================================================
# Validation
# ============================================================

def _require_int(name, value, minimum, maximum):
    if not isinstance(value, int):
        raise InvalidField(f"{name} must be an integer")

    if value < minimum or value > maximum:
        raise InvalidField(f"{name} must be between {minimum} and {maximum}")


def validate_message(message: Message):

    # Validate a PRTCP message before serialization.

    if isinstance(message, ReqJoin):

        # 00000 = find random connection
        if message.session != 0:
            _require_int(
                "SESSION",
                message.session,
                MIN_SESSION_ID,
                MAX_SESSION_ID
            )

    elif isinstance(message, AnsJoin):

        _require_int("SESSION", message.session, MIN_SESSION_ID, MAX_SESSION_ID)
        _require_int("PORT", message.port, 1, MAX_PORT)
        _require_int("CANVASX", message.canvas_x, 1, MAX_CANVAS_X)
        _require_int("CANVASY", message.canvas_y, 1, MAX_CANVAS_Y)

    elif isinstance(message, ReqDraw):

        _require_int("X", message.x, 0, MAX_COORDINATE)
        _require_int("Y", message.y, 0, MAX_COORDINATE)
        _require_int("R", message.r, 0, MAX_RGB)
        _require_int("G", message.g, 0, MAX_RGB)
        _require_int("B", message.b, 0, MAX_RGB)
        _require_int("BSIZE", message.brush_size, 0, MAX_BRUSH_SIZE)

    elif isinstance(message, AnsUpdate):

        _require_int("X", message.x, 0, MAX_COORDINATE)
        _require_int("Y", message.y, 0, MAX_COORDINATE)
        _require_int("R", message.r, 0, MAX_RGB)
        _require_int("G", message.g, 0, MAX_RGB)
        _require_int("B", message.b, 0, MAX_RGB)
        _require_int("BSIZE", message.brush_size, 0, MAX_BRUSH_SIZE)

    elif isinstance(message, AnsError):

        _require_int("ERRCODE", message.error_code, 0, MAX_ERROR_CODE)

# ============================================================
# Serialization -> Byte
# ============================================================

def serialize(message: Message) -> bytes:

    validate_message(message)

    lines = [message.type.value]

    if isinstance(message, ReqJoin):

        lines.append(f"SESSION={message.session:05d}")

    elif isinstance(message, AnsJoin):

        lines.append(f"SESSION={message.session:05d}")
        lines.append(f"PORT={message.port:05d}")
        lines.append(f"CANVASX={message.canvas_x:04d}")
        lines.append(f"CANVASY={message.canvas_y:04d}")

    elif isinstance(message, ReqDraw):

        lines.append(f"X={message.x:04d}")
        lines.append(f"Y={message.y:04d}")
        lines.append(f"R={message.r:03d}")
        lines.append(f"G={message.g:03d}")
        lines.append(f"B={message.b:03d}")
        lines.append(f"BSIZE={message.brush_size}")

    elif isinstance(message, AnsUpdate):

        lines.append(f"X={message.x:04d}")
        lines.append(f"Y={message.y:04d}")
        lines.append(f"R={message.r:03d}")
        lines.append(f"G={message.g:03d}")
        lines.append(f"B={message.b:03d}")
        lines.append(f"BSIZE={message.brush_size}")

    elif isinstance(message, AnsError):

        lines.append(f"ERRCODE={message.error_code:04d}")
        header = "\r\n".join(lines) + "\r\n\r\n"

        return (header.encode("ascii"))

    elif isinstance(message, RegSession):
        
        lines.append(f"SESSION={message.session:05d}")
        lines.append(f"PORT={message.port:05d}")
        lines.append(f"CANVASX={message.canvas_x:04d}")
        lines.append(f"CANVASY={message.canvas_y:04d}")

    # Message with no payload
    #
    # REQLEAVE
    # ANSLEAVE
    # PING
    # PONG
    #
    # Simply just contain their message type

    header = "\r\n".join(lines) + "\r\n\r\n"

    return header.encode("ascii")

# ========================================================================================================================
# PARSING
# ========================================================================================================================

# ============================================================
# Parsing helpers
# ============================================================

def _parse_int(fields, name):
    if name not in fields:
        raise MissingField(f"Missing field: {name}")

    try:
        return int(fields[name])
    except ValueError:
        raise InvalidField(f"{name} must be an integer")


def _check_exact_fields(fields, required):

    # Make sure there are no missing or unexpected fields.

    actual = set(fields.keys())
    expected = set(required)

    missing = expected - actual
    extra = actual - expected

    if missing:
        raise MissingField(f"Missing field(s): {', '.join(sorted(missing))}")

    if extra:
        raise InvalidField(f"Unexpected field(s): {', '.join(sorted(extra))}")


# ============================================================
# Parsing -> Message
# ============================================================

def parse(data: bytes) -> Message:

    # Parse one complete PRTCP message.

    if not isinstance(data, bytes):
        raise TypeError("parse() expects bytes")

    separator = b"\r\n\r\n"

    header_end = data.find(separator)

    # Error Messages

    if header_end == -1:
        raise InvalidMessage("Message header is incomplete")

    header_bytes = data[:header_end]

    try:
        header = header_bytes.decode("ascii")
    except UnicodeDecodeError:
        raise InvalidMessage("Protocol header must contain ASCII characters")

    lines = header.split("\r\n")

    if len(lines) == 0 or not lines[0]:
        raise InvalidMessage("Missing message type")

    type_string = lines[0]

    try:
        message_type = MessageType(type_string)
    except ValueError:
        raise InvalidMessageType(f"Unknown message type: {type_string}")

    fields = {}

    for line in lines[1:]:

        if "=" not in line:
            raise InvalidMessage(f"Invalid field: {line}")

        name, value = line.split("=", 1)

        if not name:
            raise InvalidMessage("Empty field name")

        if name in fields:
            raise InvalidMessage(f"Duplicate field: {name}")

        fields[name] = value

    # --------------------------------------------------------
    # REQJOIN
    # --------------------------------------------------------

    if message_type == MessageType.REQJOIN:

        _check_exact_fields(fields, ["SESSION"])

        return ReqJoin(_parse_int(fields, "SESSION"))

    # --------------------------------------------------------
    # ANSJOIN
    # --------------------------------------------------------

    if message_type == MessageType.ANSJOIN:

        _check_exact_fields(
            fields,
            [
                "SESSION",
                "PORT",
                "CANVASX",
                "CANVASY"
            ]
        )

        return AnsJoin(
            _parse_int(fields, "SESSION"),
            _parse_int(fields, "PORT"),
            _parse_int(fields, "CANVASX"),
            _parse_int(fields, "CANVASY")
        )

    # --------------------------------------------------------
    # REQDRAW
    # --------------------------------------------------------

    if message_type == MessageType.REQDRAW:

        _check_exact_fields(
            fields,
            [
                "X",
                "Y",
                "R",
                "G",
                "B",
                "BSIZE"
            ]
        )

        return ReqDraw(
            _parse_int(fields, "X"),
            _parse_int(fields, "Y"),
            _parse_int(fields, "R"),
            _parse_int(fields, "G"),
            _parse_int(fields, "B"),
            _parse_int(fields, "BSIZE")
        )

    # --------------------------------------------------------
    # ANSUPDATE
    # --------------------------------------------------------

    if message_type == MessageType.ANSUPDATE:

        _check_exact_fields(
            fields,
            [
                "X",
                "Y",
                "R",
                "G",
                "B",
                "BSIZE"
            ]
        )

        return AnsUpdate(
            _parse_int(fields, "X"),
            _parse_int(fields, "Y"),
            _parse_int(fields, "R"),
            _parse_int(fields, "G"),
            _parse_int(fields, "B"),
            _parse_int(fields, "BSIZE")
        )

    # --------------------------------------------------------
    # REQLEAVE
    # --------------------------------------------------------

    if message_type == MessageType.REQLEAVE:

        _check_exact_fields(fields, [])

        return ReqLeave()

    # --------------------------------------------------------
    # ANSLEAVE
    # --------------------------------------------------------

    if message_type == MessageType.ANSLEAVE:

        _check_exact_fields(fields, [])

        return AnsLeave()

    # --------------------------------------------------------
    # PING
    # --------------------------------------------------------

    if message_type == MessageType.PING:

        _check_exact_fields(fields, [])

        return Ping()

    # --------------------------------------------------------
    # PONG
    # --------------------------------------------------------

    if message_type == MessageType.PONG:

        _check_exact_fields(fields, [])

        return Pong()

    # --------------------------------------------------------
    # ANSERROR
    # --------------------------------------------------------

    if message_type == MessageType.ANSERROR:

        _check_exact_fields(
            fields,
            [
                "ERRCODE"
            ]
        )

        return AnsError(
            _parse_int(fields, "ERRCODE")
        )

    if message_type == MessageType.REGSESSION:
    
        _check_exact_fields(
            fields,
            [
                "SESSION",
                "PORT",
                "CANVASX",
                "CANVASY"
            ]
        )

        return RegSession(
            _parse_int(fields, "SESSION"),
            _parse_int(fields, "PORT"),
            _parse_int(fields, "CANVASX"),
            _parse_int(fields, "CANVASY")
        )
    
    if message_type == MessageType.ACKREG:

        _check_exact_fields(fields, [])

        return AckReg()

    raise InvalidMessageType(f"Unhandled message type: {message_type.value}")