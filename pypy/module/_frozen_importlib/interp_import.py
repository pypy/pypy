from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError

def import_with_frames_removed(space, __args__):
    try:
        return space.call_args(
            space.getbuiltinmodule('_frozen_importlib').getdictvalue(
                space, '__import__'), __args__)
    except OperationError as e:
        e.remove_traceback_module_frames(
            '<builtin>/frozen importlib._bootstrap')
        raise
import_with_frames_removed = interp2app(import_with_frames_removed,
                                        app_name='__import__')
