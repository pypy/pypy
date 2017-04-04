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
