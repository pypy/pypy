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
    str_expandtabs, str_ljust, str_rjust, str_center, str_zfill,
    str_join, str_split, str_rsplit, str_partition, str_rpartition,
    str_splitlines, str_translate)
from pypy.objspace.std.stringtype import makebytesdata_w
from pypy.objspace.std.listtype import (
    list_append, list_extend)


bytearray_insert  = SMM('insert', 3,
                    doc="B.insert(index, int) -> None\n\n"
                    "Insert a single item into the bytearray before "
                    "the given index.")

bytearray_pop  = SMM('pop', 2, defaults=(-1,),
                    doc="B.pop([index]) -> int\n\nRemove and return a "
                    "single item from B. If no index\nargument is given, "
                    "will pop the last value.")

bytearray_remove  = SMM('remove', 2,
                    doc="B.remove(int) -> None\n\n"
                    "Remove the first occurance of a value in B.")

bytearray_reverse  = SMM('reverse', 1,
                    doc="B.reverse() -> None\n\n"
                    "Reverse the order of the values in B in place.")

bytearray_strip  = SMM('strip', 2, defaults=(None,),
                    doc="B.strip([bytes]) -> bytearray\n\nStrip leading "
                    "and trailing bytes contained in the argument.\nIf "
                    "the argument is omitted, strip ASCII whitespace.")

bytearray_lstrip  = SMM('lstrip', 2, defaults=(None,),
                    doc="B.lstrip([bytes]) -> bytearray\n\nStrip leading "
                    "bytes contained in the argument.\nIf the argument is "
                    "omitted, strip leading ASCII whitespace.")

bytearray_rstrip  = SMM('rstrip', 2, defaults=(None,),
                    doc="'B.rstrip([bytes]) -> bytearray\n\nStrip trailing "
                    "bytes contained in the argument.\nIf the argument is "
                    "omitted, strip trailing ASCII whitespace.")

def new_bytearray(space, w_bytearraytype, data):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def descr__new__(space, w_bytearraytype, __args__):
    return new_bytearray(space,w_bytearraytype, [])

@gateway.unwrap_spec(encoding='str_or_None', errors='str_or_None')
def descr__init__(space, w_self, w_source=gateway.NoneNotWrapped,
                  encoding=None, errors=None):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    assert isinstance(w_self, W_BytearrayObject)
    data = makebytesdata_w(space, w_source, encoding, errors)
    w_self.data = data


def descr_bytearray__reduce__(space, w_self):
    from pypy.objspace.std.bytearrayobject import W_BytearrayObject
    assert isinstance(w_self, W_BytearrayObject)
    w_dict = w_self.getdict(space)
    if w_dict is None:
        w_dict = space.w_None
    return space.newtuple([
        space.type(w_self), space.newtuple([
            space.wrap(''.join(w_self.data).decode('latin-1')),
            space.wrap('latin-1')]),
        w_dict])

def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 64 < val < 71:
        return val - 55
    if 96 < val < 103:
        return val - 87
    return -1

def _hexstring_to_array(space, s):
    data = []
    length = len(s)
    i = -2
    while True:
        i += 2
        while i < length and s[i] == ' ':
            i += 1
        if i >= length:
            break
        if i+1 == length:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % i))

        top = _hex_digit_to_int(s[i])
        if top == -1:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % i))
        bot = _hex_digit_to_int(s[i+1])
        if bot == -1:
            raise OperationError(space.w_ValueError, space.wrap(
                "non-hexadecimal number found in fromhex() arg at position %d" % (i+1,)))
        data.append(chr(top*16 + bot))
    return data

def descr_fromhex(space, w_type, w_hexstring):
    "bytearray.fromhex(string) -> bytearray\n\nCreate a bytearray object "
    "from a string of hexadecimal numbers.\nSpaces between two numbers are "
    "accepted.\nExample: bytearray.fromhex('B9 01EF') -> "
    "bytearray(b'\\xb9\\x01\\xef')."
    if not space.is_w(space.type(w_hexstring), space.w_unicode):
        raise OperationError(space.w_TypeError, space.wrap(
                "must be str, not %s" % space.type(w_hexstring).name))
    hexstring = space.unicode_w(w_hexstring)
    
    data = _hexstring_to_array(space, hexstring)
    # in CPython bytearray.fromhex is a staticmethod, so
    # we ignore w_type and always return a bytearray
    return new_bytearray(space, space.w_bytearray, data)

# ____________________________________________________________

bytearray_typedef = StdTypeDef("bytearray",
    __doc__ = '''bytearray() -> an empty bytearray
bytearray(sequence) -> bytearray initialized from sequence\'s items

If the argument is a bytearray, the return value is the same object.''',
    __new__ = gateway.interp2app(descr__new__),
    __init__ = gateway.interp2app(descr__init__),
    __hash__ = None,
    __reduce__ = gateway.interp2app(descr_bytearray__reduce__),
    fromhex = gateway.interp2app(descr_fromhex, as_classmethod=True)
    )
bytearray_typedef.registermethods(globals())
