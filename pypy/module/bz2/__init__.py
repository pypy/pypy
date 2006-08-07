from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'BZ2File': 'interp_bz2.BZ2File',
        'BZ2Compressor': 'interp_bz2.BZ2Compressor',
        'BZ2Decompressor': 'interp_bz2.BZ2Decompressor',
    }

    appleveldefs = {
        '__doc__': 'app_bz2.__doc__'
    }
