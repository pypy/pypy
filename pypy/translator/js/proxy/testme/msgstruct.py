from struct import pack, unpack, calcsize

try:
    from localmsg import PORTS
except ImportError:
    PORTS = {}
try:
    from localmsg import HOSTNAME
except ImportError:
    from socket import gethostname
    HOSTNAME = gethostname()


MSG_WELCOME = "Welcome to gamesrv.py(3) !\n"
MSG_BROADCAST_PORT= "*"
MSG_DEF_PLAYFIELD = "p"
MSG_DEF_KEY       = "k"
MSG_DEF_ICON      = "r"
MSG_DEF_BITMAP    = "m"
MSG_DEF_SAMPLE    = "w"
MSG_DEF_MUSIC     = "z"
MSG_PLAY_MUSIC    = "Z"
MSG_FADEOUT       = "f"
MSG_PLAYER_JOIN   = "+"
MSG_PLAYER_KILL   = "-"
MSG_PLAYER_ICON   = "i"
MSG_PING          = "g"
MSG_PONG          = "G"
MSG_INLINE_FRAME  = "\\"
MSG_PATCH_FILE    = MSG_DEF_MUSIC
MSG_ZPATCH_FILE   = "P"
MSG_MD5_FILE      = "M"
MSG_RECORDED      = "\x00"

CMSG_PROTO_VERSION= "v"
CMSG_KEY          = "k"
CMSG_ADD_PLAYER   = "+"
CMSG_REMOVE_PLAYER= "-"
CMSG_UDP_PORT     = "<"
CMSG_ENABLE_SOUND = "s"
CMSG_ENABLE_MUSIC = "m"
CMSG_PING         = "g"
CMSG_PONG         = "G"
CMSG_DATA_REQUEST = "M"
CMSG_PLAYER_NAME  = "n"

BROADCAST_MESSAGE = "game!"   # less than 6 bytes


def message(tp, *values):
    strtype = type('')
    typecodes = ['']
    for v in values:
        if type(v) is strtype:
            typecodes.append('%ds' % len(v))
        elif 0 <= v < 256:
            typecodes.append('B')
        else:
            typecodes.append('l')
    typecodes = ''.join(typecodes)
    assert len(typecodes) < 256
    return pack(("!B%dsc" % len(typecodes)) + typecodes,
                len(typecodes), typecodes, tp, *values)

def decodemessage(data):
    if data:
        limit = ord(data[0]) + 1
        if len(data) >= limit:
            typecodes = "!c" + data[1:limit]
            try:
                end = limit + calcsize(typecodes)
            except TypeError:
                return None, ''
            if len(data) >= end:
                return unpack(typecodes, data[limit:end]), data[end:]
            elif end > 1000000:
                raise OverflowError
    return None, data
