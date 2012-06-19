from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        'nonstandard_integer_types': 'misc.nonstandard_integer_types',

        'load_library': 'libraryobj.load_library',

        'new_primitive_type': 'newtype.new_primitive_type',

        'cast': 'func.cast',
        }
