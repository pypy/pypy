import sys
from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM, no_hash_descr


bytearray_count = SMM(
    "count", 2,
    doc="B.count(sub [,start [,end]]) -> int\n"
    "Return the number of non-overlapping occurrences of subsection sub in\n"
    "bytes B[start:end].  Optional arguments start and end are interpreted\n"
    "as in slice notation.")

bytearray_index = SMM("index", 4, defaults=(0, sys.maxint),
                  doc="index(obj, [start, [stop]]) -> first index that obj "
                  "appears in the bytearray")

@gateway.unwrap_spec(ObjSpace, W_Root, W_Root, W_Root, W_Root)
def descr__new__(space, w_bytearraytype,
                 w_source='', w_encoding=None, w_errors=None):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    if w_source is None:
        data = []
    else:
        data = space.str_w(w_source)
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
