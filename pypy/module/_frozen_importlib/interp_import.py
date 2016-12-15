from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import SpaceCache


class FrozenCache(SpaceCache):
    def __init__(self, space):
        mod = space.getbuiltinmodule('_frozen_importlib')
        self.w_frozen_import = mod.get('__import__')
        assert self.w_frozen_import is not None


def import_with_frames_removed(space, __args__):
    try:
        return space.call_args(
            space.fromcache(FrozenCache).w_frozen_import, __args__)
    except OperationError as e:
        e.remove_traceback_module_frames('<frozen importlib._bootstrap>')
        raise
import_with_frames_removed = interp2app(import_with_frames_removed,
                                        app_name='__import__')
