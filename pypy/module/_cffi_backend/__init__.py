from pypy.interpreter.mixedmodule import MixedModule
from rpython.rlib import rdynload


class Module(MixedModule):

    appleveldefs = {
        }
    interpleveldefs = {
        '__version__': 'space.wrap("0.8")',

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
        'getcname': 'func.getcname',
        'newp_handle': 'handle.newp_handle',
        'from_handle': 'handle.from_handle',
        '_get_types': 'func._get_types',

        'string': 'func.string',
        'buffer': 'cbuffer.buffer',

        'get_errno': 'cerrno.get_errno',
        'set_errno': 'cerrno.set_errno',

        'FFI_DEFAULT_ABI': 'ctypefunc._get_abi(space, "FFI_DEFAULT_ABI")',
        'FFI_CDECL': 'ctypefunc._get_abi(space,"FFI_DEFAULT_ABI")',#win32 name
        }

for _name in ["RTLD_LAZY", "RTLD_NOW", "RTLD_GLOBAL", "RTLD_LOCAL",
              "RTLD_NODELETE", "RTLD_NOLOAD", "RTLD_DEEPBIND"]:
    if getattr(rdynload.cConfig, _name) is not None:
        Module.interpleveldefs[_name] = 'space.wrap(%d)' % (
            getattr(rdynload.cConfig, _name),)

for _name in ["RTLD_LAZY", "RTLD_NOW", "RTLD_GLOBAL", "RTLD_LOCAL"]:
    Module.interpleveldefs.setdefault(_name, 'space.wrap(0)')
