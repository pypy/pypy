import os
from pypy.objspace.flow.model import SpaceOperation


class CType(object):

    def __init__(self, translator):
        self.translator = translator

    def debugname(self):
        return self.typename

    def genc():
        """A hack to get at the currently running GenC instance."""
        from pypy.translator.genc.genc import TLS
        return TLS.genc
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
