import sys
from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM, no_hash_descr

from pypy.objspace.std.stringtype import (
    str_count, str_index, str_rindex, str_find, str_rfind, str_replace,
    str_startswith, str_endswith, str_islower, str_isupper, str_isalpha,
    str_isalnum, str_isdigit, str_isspace, str_istitle,
    str_upper, str_lower, str_title, str_swapcase, str_capitalize,
    str_expandtabs, str_lstrip, str_rstrip, str_strip,
    str_ljust, str_rjust, str_center, str_zfill,
    str_join, str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines)

@gateway.unwrap_spec(ObjSpace, W_Root, W_Root, W_Root, W_Root)
def descr__new__(space, w_bytearraytype,
                 w_source='', w_encoding=None, w_errors=None):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    data = [c for c in space.str_w(w_source)]
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj

# ____________________________________________________________

bytearray_typedef = StdTypeDef("bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = no_hash_descr,
    )
bytearray_typedef.registermethods(globals())
