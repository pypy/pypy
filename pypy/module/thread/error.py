from pypy.interpreter.error import OperationError

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("thread.error")

def wrap_thread_error(space, msg):
    w_error = space.fromcache(Cache).w_error
    return OperationError(w_error, space.wrap(msg))
