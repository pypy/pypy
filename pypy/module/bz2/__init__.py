from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):
    interpleveldefs = {
        'BZ2File': 'interp_bz2.BZ2File',
    }

    appleveldefs = {
        '__doc__': 'app_bz2.__doc__'
    }
