# some exception classes for the Smalltalk VM

class SmalltalkException(Exception):
    """Base class for Smalltalk exception hierarchy"""

class PrimitiveFailedError(SmalltalkException):
    pass

class PrimitiveNotYetWrittenError(PrimitiveFailedError):
    pass

class UnwrappingError(PrimitiveFailedError):
    pass

class WrappingError(PrimitiveFailedError):
    pass

class WrapperException(SmalltalkException):
    def __init__(self, msg):
        self.msg = msg

class FatalError(SmalltalkException):
    def __init__(self, msg):
        self.msg = msg
