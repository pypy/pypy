# REVIEWME
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    """The python bz2 module provides a comprehensive interface for
the bz2 compression library. It implements a complete file
interface, one shot (de)compression functions, and types for
sequential (de)compression."""

    interpleveldefs = {
        'BZ2Compressor': 'interp_bz2.W_BZ2Compressor',
        'BZ2Decompressor': 'interp_bz2.W_BZ2Decompressor',
        'compress': 'interp_bz2.compress',
        'decompress': 'interp_bz2.decompress',
        'BZ2File': 'interp_bz2.W_BZ2File',
    }

    appleveldefs = {
    }

    def startup(self, space):
        from pypy.module.bz2 import interp_bz2
        space.setitem(self.w_dict, space.newtext('bzlib_version'),
                      space.newtext(interp_bz2.bzlib_version()))
        space.setitem(self.w_dict, space.newtext('bzlib_version_info'),
                      interp_bz2.get_version_info(space))
