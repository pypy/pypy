import sys
from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stdtypedef import StdTypeDef, SMM

from pypy.objspace.std.stringtype import (
    str_decode,
    str_count, str_index, str_rindex, str_find, str_rfind, str_replace,
    str_startswith, str_endswith, str_islower, str_isupper, str_isalpha,
    str_isalnum, str_isdigit, str_isspace, str_istitle,
    str_upper, str_lower, str_title, str_swapcase, str_capitalize,
    str_expandtabs, str_lstrip, str_rstrip, str_strip,
    str_ljust, str_rjust, str_center, str_zfill,
    str_join, str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines, str_translate)
from pypy.objspace.std.listtype import (
    list_append, list_extend)

def getbytevalue(space, w_value):
    if space.isinstance_w(w_value, space.w_str):
        string = space.str_w(w_value)
        if len(string) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "string must be of size 1"))
        return string[0]

    value = space.getindex_w(w_value, None)
    if not 0 <= value < 256:
        # this includes the OverflowError in case the long is too large
        raise OperationError(space.w_ValueError, space.wrap(
            "byte must be in range(0, 256)"))
    return chr(value)

def new_bytearray(space, w_bytearraytype, data):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj

@gateway.unwrap_spec(ObjSpace, W_Root, W_Root, W_Root, W_Root)
def descr__new__(space, w_bytearraytype,
                 w_source='', w_encoding=None, w_errors=None):
    data = []
    # Unicode argument
    if not space.is_w(w_encoding, space.w_None):
        from pypy.objspace.std.unicodetype import (
            _get_encoding_and_errors, encode_object
        )
        encoding, errors = _get_encoding_and_errors(space, w_encoding, space.w_None)

        # if w_source is an integer this correctly raises a TypeError
        # the CPython error message is: "encoding or errors without a string argument"
        # ours is: "expected unicode, got int object"
        w_source = encode_object(space, w_source, encoding, errors)

    # String-like argument
    try:
        string = space.str_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        data = [c for c in string]
        return new_bytearray(space, w_bytearraytype, data)

    # Is it an int?
    try:
        count = space.int_w(w_source)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        data = ['\0'] * count
        return new_bytearray(space, w_bytearraytype, data)

    # sequence of bytes
    w_iter = space.iter(w_source)
    while True:
        try:
            w_item = space.next(w_iter)
        except OperationError, e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        value = getbytevalue(space, w_item)
        data.append(value)

    return new_bytearray(space, w_bytearraytype, data)

@gateway.unwrap_spec(gateway.ObjSpace, gateway.W_Root)
def descr_bytearray__reduce__(space, w_self):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    assert isinstance(w_self, W_BytearrayObject)
    w_dict = w_self.getdict()
    if w_dict is None:
        w_dict = space.w_None
    return space.newtuple([
        space.type(w_self), space.newtuple([
            space.wrap(''.join(w_self.data).decode('latin-1')),
            space.wrap('latin-1')]),
        w_dict])

# ____________________________________________________________

bytearray_typedef = StdTypeDef("bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = gateway.interp2app(descr__new__),
    __hash__ = None,
    __reduce__ = gateway.interp2app(descr_bytearray__reduce__),
    )
bytearray_typedef.registermethods(globals())
