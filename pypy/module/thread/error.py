from pypy.interpreter.error import OperationError

def reraise_thread_error(space, msg):
    w_module = space.getbuiltinmodule('thread')
    w_error = space.getattr(w_module, space.wrap('error'))
    raise OperationError(w_error, space.wrap(msg))
