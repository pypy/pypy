from pypy.interpreter.error import OperationError

def raise_Error(space, msg):
    w_module = space.getbuiltinmodule('binascii')
    w_Error = space.getattr(w_module, space.wrap('Error'))
    raise OperationError(w_Error, space.wrap(msg))

def raise_Incomplete(space, msg):
    w_module = space.getbuiltinmodule('binascii')
    w_Error = space.getattr(w_module, space.wrap('Incomplete'))
    raise OperationError(w_Error, space.wrap(msg))
