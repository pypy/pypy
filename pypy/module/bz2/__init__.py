# REVIEWME
from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'BZ2Compressor': 'interp_bz2.W_BZ2Compressor',
        'BZ2Decompressor': 'interp_bz2.W_BZ2Decompressor',
        'compress': 'interp_bz2.compress',
        'decompress': 'interp_bz2.decompress',
        '_open_file_as_stream': 'interp_bz2.open_file_as_stream'
    }

    appleveldefs = {
        '__doc__': 'app_bz2.__doc__',
        'BZ2File': 'app_bz2.BZ2File',
    }
