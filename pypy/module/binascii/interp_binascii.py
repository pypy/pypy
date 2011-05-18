from pypy.interpreter.error import OperationError

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("binascii.Error")
        self.w_incomplete = space.new_exception_class("binascii.Incomplete")

def raise_Error(space, msg):
    w_error = space.fromcache(Cache).w_error
    raise OperationError(w_error, space.wrap(msg))

def raise_Incomplete(space, msg):
    w_error = space.fromcache(Cache).w_incomplete
    raise OperationError(w_error, space.wrap(msg))
