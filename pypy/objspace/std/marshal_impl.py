from rpython.rlib.rarithmetic import LONG_BIT, r_longlong, r_uint
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.rstruct import ieee
from rpython.rlib.unroll import unrolling_iterable

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.special import Ellipsis
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import unicodehelper
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.objspace.std.bytesobject import W_BytesObject
from pypy.objspace.std.complexobject import W_ComplexObject
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.listobject import W_ListObject
from pypy.objspace.std.longobject import W_AbstractLongObject
from pypy.objspace.std.noneobject import W_NoneObject
from pypy.objspace.std.setobject import W_FrozensetObject, W_SetObject
from pypy.objspace.std.tupleobject import W_AbstractTupleObject
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject


TYPE_NULL      = '0'
TYPE_NONE      = 'N'
TYPE_FALSE     = 'F'
TYPE_TRUE      = 'T'
TYPE_STOPITER  = 'S'
TYPE_ELLIPSIS  = '.'
TYPE_INT       = 'i'
TYPE_INT64     = 'I'
TYPE_FLOAT     = 'f'
TYPE_BINARY_FLOAT = 'g'
TYPE_COMPLEX   = 'x'
TYPE_BINARY_COMPLEX = 'y'
TYPE_LONG      = 'l'
TYPE_STRING    = 's'
TYPE_STRINGREF = 'R'
TYPE_TUPLE     = '('
TYPE_LIST      = '['
TYPE_DICT      = '{'
TYPE_CODE      = 'c'
TYPE_UNICODE   = 'u'
TYPE_UNKNOWN   = '?'
TYPE_SET       = '<'
TYPE_FROZENSET = '>'


_marshallers = []
_unmarshallers = []

def marshaller(type):
    def _decorator(f):
        _marshallers.append((type, f))
        return f
    return _decorator

def unmarshaller(tc):
    def _decorator(f):
        _unmarshallers.append((tc, f))
        return f
    return _decorator

def marshal(space, w_obj, m):
    # _marshallers_unroll is defined at the end of the file
    # NOTE that if w_obj is a heap type, like an instance of a
    # user-defined subclass, then we skip that part completely!
    if not space.type(w_obj).is_heaptype():
        for type, func in _marshallers_unroll:
            if isinstance(w_obj, type):
                func(space, w_obj, m)
                return

    # any unknown object implementing the buffer protocol is
    # accepted and encoded as a plain string
    try:
        s = space.readbuf_w(w_obj)
    except OperationError as e:
        if e.match(space, space.w_TypeError):
            raise oefmt(space.w_ValueError, "unmarshallable object")
        raise
    m.atom_str(TYPE_STRING, s.as_str())

def get_unmarshallers():
    return _unmarshallers


@marshaller(W_NoneObject)
def marshal_none(space, w_none, m):
    m.atom(TYPE_NONE)

@unmarshaller(TYPE_NONE)
def unmarshal_none(space, u, tc):
    return space.w_None


@marshaller(W_BoolObject)
def marshal_bool(space, w_bool, m):
    m.atom(TYPE_TRUE if w_bool.intval else TYPE_FALSE)

@unmarshaller(TYPE_TRUE)
def unmarshal_bool(space, u, tc):
    return space.w_True

@unmarshaller(TYPE_FALSE)
def unmarshal_false(space, u, tc):
    return space.w_False


@marshaller(W_TypeObject)
def marshal_stopiter(space, w_type, m):
    if not space.is_w(w_type, space.w_StopIteration):
        raise oefmt(space.w_ValueError, "unmarshallable object")
    m.atom(TYPE_STOPITER)

@unmarshaller(TYPE_STOPITER)
def unmarshal_stopiter(space, u, tc):
    return space.w_StopIteration


@marshaller(Ellipsis)
def marshal_ellipsis(space, w_ellipsis, m):
    m.atom(TYPE_ELLIPSIS)

@unmarshaller(TYPE_ELLIPSIS)
def unmarshal_ellipsis(space, u, tc):
    return space.w_Ellipsis


@marshaller(W_IntObject)
def marshal_int(space, w_int, m):
    if LONG_BIT == 32:
        m.atom_int(TYPE_INT, w_int.intval)
    else:
        y = w_int.intval >> 31
        if y and y != -1:
            m.atom_int64(TYPE_INT64, w_int.intval)
        else:
            m.atom_int(TYPE_INT, w_int.intval)

@unmarshaller(TYPE_INT)
def unmarshal_int(space, u, tc):
    return space.newint(u.get_int())

@unmarshaller(TYPE_INT64)
def unmarshal_int64(space, u, tc):
    lo = u.get_int()    # get the first 32 bits
    hi = u.get_int()    # get the next 32 bits
    if LONG_BIT >= 64:
        x = (hi << 32) | (lo & (2**32-1))    # result fits in an int
    else:
        x = (r_longlong(hi) << 32) | r_longlong(r_uint(lo))  # get a r_longlong
    return space.wrap(x)


@marshaller(W_AbstractLongObject)
def marshal_long(space, w_long, m):
    from rpython.rlib.rarithmetic import r_ulonglong
    m.start(TYPE_LONG)
    SHIFT = 15
    MASK = (1 << SHIFT) - 1
    num = w_long.asbigint()
    sign = num.sign
    num = num.abs()
    total_length = (num.bit_length() + (SHIFT - 1)) / SHIFT
    m.put_int(total_length * sign)
    bigshiftcount = r_ulonglong(0)
    for i in range(total_length):
        next = num.abs_rshift_and_mask(bigshiftcount, MASK)
        m.put_short(next)
        bigshiftcount += SHIFT

@unmarshaller(TYPE_LONG)
def unmarshal_long(space, u, tc):
    from rpython.rlib.rbigint import rbigint
    lng = u.get_int()
    if lng < 0:
        negative = True
        lng = -lng
    else:
        negative = False
    digits = [u.get_short() for i in range(lng)]
    result = rbigint.from_list_n_bits(digits, 15)
    if lng and not result.tobool():
        raise oefmt(space.w_ValueError, "bad marshal data")
    if negative:
        result = result.neg()
    return space.newlong_from_rbigint(result)


def pack_float(f):
    result = StringBuilder(8)
    ieee.pack_float(result, f, 8, False)
    return result.build()

def unpack_float(s):
    return ieee.unpack_float(s, False)

@marshaller(W_FloatObject)
def marshal_float(space, w_float, m):
    if m.version > 1:
        m.start(TYPE_BINARY_FLOAT)
        m.put(pack_float(w_float.floatval))
    else:
        m.start(TYPE_FLOAT)
        m.put_pascal(space.str_w(space.repr(w_float)))

@unmarshaller(TYPE_FLOAT)
def unmarshal_float(space, u, tc):
    return space.call_function(space.builtin.get('float'),
                               space.wrap(u.get_pascal()))

@unmarshaller(TYPE_BINARY_FLOAT)
def unmarshal_float_bin(space, u, tc):
    return space.newfloat(unpack_float(u.get(8)))


@marshaller(W_ComplexObject)
def marshal_complex(space, w_complex, m):
    if m.version > 1:
        m.start(TYPE_BINARY_COMPLEX)
        m.put(pack_float(w_complex.realval))
        m.put(pack_float(w_complex.imagval))
    else:
        # XXX a bit too wrap-happy
        w_real = space.wrap(w_complex.realval)
        w_imag = space.wrap(w_complex.imagval)
        m.start(TYPE_COMPLEX)
        m.put_pascal(space.str_w(space.repr(w_real)))
        m.put_pascal(space.str_w(space.repr(w_imag)))

@unmarshaller(TYPE_COMPLEX)
def unmarshal_complex(space, u, tc):
    w_real = space.call_function(space.builtin.get('float'),
                                 space.wrap(u.get_pascal()))
    w_imag = space.call_function(space.builtin.get('float'),
                                 space.wrap(u.get_pascal()))
    w_t = space.builtin.get('complex')
    return space.call_function(w_t, w_real, w_imag)

@unmarshaller(TYPE_BINARY_COMPLEX)
def unmarshal_complex_bin(space, u, tc):
    real = unpack_float(u.get(8))
    imag = unpack_float(u.get(8))
    return space.newcomplex(real, imag)


@marshaller(W_BytesObject)
def marshal_bytes(space, w_str, m):
    s = w_str.unwrap(space)
    m.atom_str(TYPE_STRING, s)

@unmarshaller(TYPE_STRING)
def unmarshal_bytes(space, u, tc):
    return space.newbytes(u.get_str())

@unmarshaller(TYPE_STRINGREF)
def unmarshal_stringref(space, u, tc):
    idx = u.get_int()
    try:
        return u.stringtable_w[idx]
    except IndexError:
        raise oefmt(space.w_ValueError, "bad marshal data")


@marshaller(W_AbstractTupleObject)
def marshal_tuple(space, w_tuple, m):
    items = w_tuple.tolist()
    m.put_tuple_w(TYPE_TUPLE, items)

@unmarshaller(TYPE_TUPLE)
def unmarshal_tuple(space, u, tc):
    items_w = u.get_tuple_w()
    return space.newtuple(items_w)


@marshaller(W_ListObject)
def marshal_list(space, w_list, m):
    items = w_list.getitems()[:]
    m.put_tuple_w(TYPE_LIST, items)

@unmarshaller(TYPE_LIST)
def unmarshal_list(space, u, tc):
    items_w = u.get_list_w()
    return space.newlist(items_w)


@marshaller(W_DictMultiObject)
def marshal_dict(space, w_dict, m):
    m.start(TYPE_DICT)
    for w_tuple in w_dict.items():
        w_key, w_value = space.fixedview(w_tuple, 2)
        m.put_w_obj(w_key)
        m.put_w_obj(w_value)
    m.atom(TYPE_NULL)

@unmarshaller(TYPE_DICT)
def unmarshal_dict(space, u, tc):
    # since primitive lists are not optimized and we don't know
    # the dict size in advance, use the dict's setitem instead
    # of building a list of tuples.
    w_dic = space.newdict()
    while 1:
        w_key = u.get_w_obj(allow_null=True)
        if w_key is None:
            break
        w_value = u.get_w_obj()
        space.setitem(w_dic, w_key, w_value)
    return w_dic

@unmarshaller(TYPE_NULL)
def unmarshal_NULL(self, u, tc):
    return None


def _put_str_list(space, m, strlist):
    m.atom_int(TYPE_TUPLE, len(strlist))
    atom_str = m.atom_str
    for item in strlist:
        atom_str(TYPE_STRING, item)

@marshaller(PyCode)
def marshal_pycode(space, w_pycode, m):
    m.start(TYPE_CODE)
    # see pypy.interpreter.pycode for the layout
    x = space.interp_w(PyCode, w_pycode)
    m.put_int(x.co_argcount)
    m.put_int(x.co_kwonlyargcount)
    m.put_int(x.co_nlocals)
    m.put_int(x.co_stacksize)
    m.put_int(x.co_flags)
    m.atom_str(TYPE_STRING, x.co_code)
    m.put_tuple_w(TYPE_TUPLE, x.co_consts_w)
    _put_str_list(space, m, [space.str_w(w_name) for w_name in x.co_names_w])
    _put_str_list(space, m, x.co_varnames)
    _put_str_list(space, m, x.co_freevars)
    _put_str_list(space, m, x.co_cellvars)
    m.atom_str(TYPE_STRING, x.co_filename)
    m.atom_str(TYPE_STRING, x.co_name)
    m.put_int(x.co_firstlineno)
    m.atom_str(TYPE_STRING, x.co_lnotab)

# helper for unmarshalling "tuple of string" objects
# into rpython-level lists of strings.  Only for code objects.

def unmarshal_str(u):
    w_obj = u.get_w_obj()
    try:
        return u.space.bytes_w(w_obj)
    except OperationError as e:
        if e.match(u.space, u.space.w_TypeError):
            u.raise_exc('invalid marshal data for code object')
        else:
            raise

def unmarshal_str0(u):
    w_obj = u.get_w_obj()
    try:
        return u.space.bytes0_w(w_obj)
    except OperationError as e:
        if e.match(u.space, u.space.w_TypeError):
            u.raise_exc('invalid marshal data for code object')
        raise

def unmarshal_strlist(u, tc):
    lng = u.atom_lng(tc)
    return [unmarshal_str(u) for i in range(lng)]

@unmarshaller(TYPE_CODE)
def unmarshal_pycode(space, u, tc):
    argcount    = u.get_int()
    kwonlyargcount = u.get_int()
    nlocals     = u.get_int()
    stacksize   = u.get_int()
    flags       = u.get_int()
    code        = unmarshal_str(u)
    u.start(TYPE_TUPLE)
    consts_w    = u.get_tuple_w()
    # copy in order not to merge it with anything else
    names       = unmarshal_strlist(u, TYPE_TUPLE)
    varnames    = unmarshal_strlist(u, TYPE_TUPLE)
    freevars    = unmarshal_strlist(u, TYPE_TUPLE)
    cellvars    = unmarshal_strlist(u, TYPE_TUPLE)
    filename    = unmarshal_str0(u)
    name        = unmarshal_str(u)
    firstlineno = u.get_int()
    lnotab      = unmarshal_str(u)
    return PyCode(space, argcount, kwonlyargcount, nlocals, stacksize, flags,
                  code, consts_w[:], names, varnames, filename,
                  name, firstlineno, lnotab, freevars, cellvars)


@marshaller(W_UnicodeObject)
def marshal_unicode(space, w_unicode, m):
    s = unicodehelper.encode_utf8(space, space.unicode_w(w_unicode),
                                  allow_surrogates=True)
    m.atom_str(TYPE_UNICODE, s)

@unmarshaller(TYPE_UNICODE)
def unmarshal_unicode(space, u, tc):
    return space.wrap(unicodehelper.decode_utf8(space, u.get_str(),
                                                allow_surrogates=True))

@marshaller(W_SetObject)
def marshal_set(space, w_set, m):
    lis_w = space.fixedview(w_set)
    m.put_tuple_w(TYPE_SET, lis_w)

@unmarshaller(TYPE_SET)
def unmarshal_set(space, u, tc):
    return unmarshal_set_frozenset(space, u, tc)


@marshaller(W_FrozensetObject)
def marshal_frozenset(space, w_frozenset, m):
    lis_w = space.fixedview(w_frozenset)
    m.put_tuple_w(TYPE_FROZENSET, lis_w)

def unmarshal_set_frozenset(space, u, tc):
    lng = u.get_lng()
    w_set = space.call_function(space.w_set)
    for i in xrange(lng):
        w_obj = u.get_w_obj()
        space.call_method(w_set, "add", w_obj)
    if tc == TYPE_FROZENSET:
        w_set = space.call_function(space.w_frozenset, w_set)
    return w_set

@unmarshaller(TYPE_FROZENSET)
def unmarshal_frozenset(space, u, tc):
    return unmarshal_set_frozenset(space, u, tc)


_marshallers_unroll = unrolling_iterable(_marshallers)
