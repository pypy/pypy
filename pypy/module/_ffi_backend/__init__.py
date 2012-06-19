from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        'nonstandard_integer_types':
                        'interp_extra_types.nonstandard_integer_types',
        'load_library': 'interp_library.load_library',
        }
