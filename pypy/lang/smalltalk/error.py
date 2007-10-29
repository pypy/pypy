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

