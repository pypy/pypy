from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        'load_library': 'interp_library.load_library',
        }
