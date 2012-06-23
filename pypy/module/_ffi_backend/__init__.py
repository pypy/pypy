from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        'nonstandard_integer_types': 'misc.nonstandard_integer_types',

        'load_library': 'libraryobj.load_library',

        'new_primitive_type': 'newtype.new_primitive_type',
        'new_pointer_type': 'newtype.new_pointer_type',
        'new_array_type': 'newtype.new_array_type',
        'new_struct_type': 'newtype.new_struct_type',
        'new_union_type': 'newtype.new_union_type',
        'complete_struct_or_union': 'newtype.complete_struct_or_union',

        'newp': 'func.newp',
        'cast': 'func.cast',
        'sizeof': 'func.sizeof',
        'alignof': 'func.alignof',
        '_getfields': 'func._getfields',
        }
