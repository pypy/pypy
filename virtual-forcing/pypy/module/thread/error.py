from pypy.interpreter.error import OperationError

def wrap_thread_error(space, msg):
    w_module = space.getbuiltinmodule('thread')
    w_error = space.getattr(w_module, space.wrap('error'))
    return OperationError(w_error, space.wrap(msg))
