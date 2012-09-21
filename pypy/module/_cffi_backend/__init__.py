from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        '__version__': 'space.wrap("0.3")',

        'nonstandard_integer_types': 'misc.nonstandard_integer_types',

        'load_library': 'libraryobj.load_library',

        'new_primitive_type': 'newtype.new_primitive_type',
        'new_pointer_type': 'newtype.new_pointer_type',
        'new_array_type': 'newtype.new_array_type',
        'new_struct_type': 'newtype.new_struct_type',
        'new_union_type': 'newtype.new_union_type',
        'complete_struct_or_union': 'newtype.complete_struct_or_union',
        'new_void_type': 'newtype.new_void_type',
        'new_enum_type': 'newtype.new_enum_type',
        'new_function_type': 'newtype.new_function_type',

        'newp': 'func.newp',
        'cast': 'func.cast',
        'callback': 'func.callback',
        'alignof': 'func.alignof',
        'sizeof': 'func.sizeof',
        'typeof': 'func.typeof',
        'typeoffsetof': 'func.typeoffsetof',
        'rawaddressof': 'func.rawaddressof',
        '_getfields': 'func._getfields',
        'getcname': 'func.getcname',
        '_get_types': 'func._get_types',

        'string': 'func.string',
        'buffer': 'cbuffer.buffer',

        'get_errno': 'cerrno.get_errno',
        'set_errno': 'cerrno.set_errno',

        'FFI_DEFAULT_ABI': 'ctypefunc._get_abi(space, "FFI_DEFAULT_ABI")',
        'FFI_CDECL': 'ctypefunc._get_abi(space,"FFI_DEFAULT_ABI")',#win32 name
        }
