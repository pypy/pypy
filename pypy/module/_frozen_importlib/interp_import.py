from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError

@interp2app
def __import__(space, __args__):
    try:
        return space.call_args(
            space.getbuiltinmodule('_frozen_importlib').getdictvalue(
                space, '__import__'), __args__)
    except OperationError as e:
        e.remove_traceback_module_frames('<frozen importlib._bootstrap>')
        raise
