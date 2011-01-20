"""Implementation module for socket operations.

See the socket module for documentation."""

class error(IOError):
    pass

class herror(error):
    pass

class gaierror(error):
    pass

class timeout(error):
    pass
