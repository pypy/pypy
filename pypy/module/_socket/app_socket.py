"""Implementation module for socket operations.
NOT_RPYTHON

See the socket module for documentation."""

defaulttimeout = -1 # Default timeout for new sockets

class error(Exception):
    pass

class herror(error):
    pass

class gaierror(error):
    pass

class timeout(error):
    pass

class SocketType:
    pass

socket = SocketType

def setdefaulttimeout(timeout):
    if timeout is None:
        timeout = -1.0
    else:
        if timeout < 0.0:
            raise ValueError, "Timeout value out of range"

    global defaulttimeout
    defaulttimeout = timeout

def getdefaulttimeout():
    timeout = defaulttimeout

    if timeout < 0.0:
        return None
    else:
        return timeout
