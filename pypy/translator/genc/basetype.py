import os
from pypy.objspace.flow.model import SpaceOperation
from pypy.interpreter.miscutils import getthreadlocals


class CType(object):

    def __init__(self, translator):
        self.translator = translator

    def debugname(self):
        return self.__class__.__name__

    def genc():
        """A hack to get at the currently running GenC instance."""
        return getthreadlocals().genc
    genc = staticmethod(genc)

    def init_globals(self, genc):
        return []

    def collect_globals(self, genc):
        return []

    # --- interface for ../typer.py ---

    def convert_to_obj(self, typer, v1, v2):
        return [SpaceOperation("conv_to_obj", [v1], v2)]

    def convert_from_obj(self, typer, v1, v2):
        return [SpaceOperation("conv_from_obj", [v1], v2)]
