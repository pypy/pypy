# implementation of marshalling by multimethods

"""
The idea is to have an effective but flexible
way to implement marshalling for the native types.

The marshal_w operation is called with an object,
a callback and a state variable.
"""

from pypy.interpreter.error import OperationError
from pypy.objspace.std.register_all import register_all
from pypy.rlib.rarithmetic import LONG_BIT, r_longlong, r_uint, intmask
from pypy.objspace.std import model
from pypy.interpreter.special import Ellipsis
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import gateway, unicodehelper
from pypy.rlib.rstruct import ieee

from pypy.objspace.std.boolobject    import W_BoolObject
from pypy.objspace.std.complexobject import W_ComplexObject
from pypy.objspace.std.intobject     import W_IntObject
from pypy.objspace.std.floatobject   import W_FloatObject
from pypy.objspace.std.tupleobject   import W_TupleObject
from pypy.objspace.std.listobject    import W_ListObject
from pypy.objspace.std.dictmultiobject    import W_DictMultiObject
from pypy.objspace.std.stringobject  import W_StringObject
from pypy.objspace.std.ropeobject    import W_RopeObject
from pypy.objspace.std.typeobject    import W_TypeObject
from pypy.objspace.std.longobject    import W_LongObject, newlong
from pypy.objspace.std.noneobject    import W_NoneObject
from pypy.objspace.std.unicodeobject import W_UnicodeObject

from pypy.module.marshal.interp_marshal import register

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
TYPE_INTERNED  = 't'
TYPE_STRINGREF = 'R'
TYPE_TUPLE     = '('
TYPE_LIST      = '['
TYPE_DICT      = '{'
TYPE_CODE      = 'c'
TYPE_UNICODE   = 'u'
TYPE_UNKNOWN   = '?'
TYPE_SET       = '<'
TYPE_FROZENSET = '>'

"""
simple approach:
a call to marshal_w has the following semantics:
marshal_w receives a marshaller object which contains
state and several methods.


atomic types including typecode:

atom(tc)                    puts single typecode
atom_int(tc, int)           puts code and int
atom_int64(tc, int64)       puts code and int64
atom_str(tc, str)           puts code, len and string
atom_strlist(tc, strlist)   puts code, len and list of strings

building blocks for compound types:

start(typecode)             sets the type character
put(s)                      puts a string with fixed length
put_short(int)              puts a short integer
put_int(int)                puts an integer
put_pascal(s)               puts a short string
put_w_obj(w_obj)            puts a wrapped object
put_tuple_w(TYPE, tuple_w)  puts tuple_w, an unwrapped list of wrapped objects
"""

handled_by_any = []

def raise_exception(space, msg):
    raise OperationError(space.w_ValueError, space.wrap(msg))

def marshal_w__None(space, w_none, m):
    m.atom(TYPE_NONE)

def unmarshal_None(space, u, tc):
    return space.w_None
register(TYPE_NONE, unmarshal_None)

def marshal_w__Bool(space, w_bool, m):
    if w_bool.boolval:
        m.atom(TYPE_TRUE)
    else:
        m.atom(TYPE_FALSE)

def unmarshal_Bool(space, u, tc):
    if tc == TYPE_TRUE:
        return space.w_True
    else:
        return space.w_False
register(TYPE_TRUE + TYPE_FALSE, unmarshal_Bool)

def marshal_w__Type(space, w_type, m):
    if not space.is_w(w_type, space.w_StopIteration):
        raise_exception(space, "unmarshallable object")
    m.atom(TYPE_STOPITER)

def unmarshal_Type(space, u, tc):
    return space.w_StopIteration
register(TYPE_STOPITER, unmarshal_Type)

# not directly supported:
def marshal_w_Ellipsis(space, w_ellipsis, m):
    m.atom(TYPE_ELLIPSIS)

model.MM.marshal_w.register(marshal_w_Ellipsis, Ellipsis)

def unmarshal_Ellipsis(space, u, tc):
    return space.w_Ellipsis
register(TYPE_ELLIPSIS, unmarshal_Ellipsis)

def marshal_w__Int(space, w_int, m):
    if LONG_BIT == 32:
        m.atom_int(TYPE_INT, w_int.intval)
    else:
        y = w_int.intval >> 31
        if y and y != -1:
            m.atom_int64(TYPE_INT64, w_int.intval)
        else:
            m.atom_int(TYPE_INT, w_int.intval)

def unmarshal_Int(space, u, tc):
    return space.newint(u.get_int())
register(TYPE_INT, unmarshal_Int)

def unmarshal_Int64(space, u, tc):
    lo = u.get_int()    # get the first 32 bits
    hi = u.get_int()    # get the next 32 bits
    if LONG_BIT >= 64:
        x = (hi << 32) | (lo & (2**32-1))    # result fits in an int
    else:
        x = (r_longlong(hi) << 32) | r_longlong(r_uint(lo))  # get a r_longlong
    return space.wrap(x)
register(TYPE_INT64, unmarshal_Int64)

def pack_float(f):
    result = []
    ieee.pack_float(result, f, 8, False)
    return ''.join(result)

def unpack_float(s):
    return ieee.unpack_float(s, False)

def marshal_w__Float(space, w_float, m):
    if m.version > 1:
        m.start(TYPE_BINARY_FLOAT)
        m.put(pack_float(w_float.floatval))
    else:
        m.start(TYPE_FLOAT)
        m.put_pascal(space.str_w(space.repr(w_float)))

def unmarshal_Float(space, u, tc):
    return space.call_function(space.builtin.get('float'),
                               space.wrap(u.get_pascal()))
register(TYPE_FLOAT, unmarshal_Float)

def unmarshal_Float_bin(space, u, tc):
    return space.newfloat(unpack_float(u.get(8)))
register(TYPE_BINARY_FLOAT, unmarshal_Float_bin)

def marshal_w__Complex(space, w_complex, m):
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

def unmarshal_Complex(space, u, tc):
    w_real = space.call_function(space.builtin.get('float'),
                                 space.wrap(u.get_pascal()))
    w_imag = space.call_function(space.builtin.get('float'),
                                 space.wrap(u.get_pascal()))
    w_t = space.builtin.get('complex')
    return space.call_function(w_t, w_real, w_imag)
register(TYPE_COMPLEX, unmarshal_Complex)

def unmarshal_Complex_bin(space, u, tc):
    real = unpack_float(u.get(8))
    imag = unpack_float(u.get(8))
    return space.newcomplex(real, imag)
register(TYPE_BINARY_COMPLEX, unmarshal_Complex_bin)

def marshal_w__Long(space, w_long, m):
    from pypy.rlib.rbigint import rbigint
    m.start(TYPE_LONG)
    SHIFT = 15
    MASK = (1 << SHIFT) - 1
    num = w_long.num
    sign = num.sign
    num = num.abs()
    ints = []
    while num.tobool():
        next = intmask(num.uintmask() & MASK)
        ints.append(next)
        num = num.rshift(SHIFT)
    m.put_int(len(ints) * sign)
    for i in ints:
        m.put_short(i)

def unmarshal_Long(space, u, tc):
    from pypy.rlib.rbigint import rbigint
    lng = u.get_int()
    if lng < 0:
        negative = True
        lng = -lng
    else:
        negative = False
    SHIFT = 15
    result = rbigint.fromint(0)
    for i in range(lng):
        shift = i * SHIFT
        result = result.or_(rbigint.fromint(u.get_short()).lshift(shift))
    if lng and not result.tobool():
        raise_exception(space, 'bad marshal data')
    if negative:
        result = result.neg()
    w_long = newlong(space, result)
    return w_long
register(TYPE_LONG, unmarshal_Long)

# XXX currently, intern() is at applevel,
# and there is no interface to get at the
# internal table.
# Move intern to interplevel and add a flag
# to strings.
def PySTRING_CHECK_INTERNED(w_str):
    return False

def marshal_w__String(space, w_str, m):
    # using the fastest possible access method here
    # that does not touch the internal representation,
    # which might change (array of bytes?)
    s = w_str.unwrap(space)
    if m.version >= 1 and PySTRING_CHECK_INTERNED(w_str):
        # we use a native rtyper stringdict for speed
        idx = m.stringtable.get(s, -1)
        if idx >= 0:
            m.atom_int(TYPE_STRINGREF, idx)
        else:
            idx = len(m.stringtable)
            m.stringtable[s] = idx
            m.atom_str(TYPE_INTERNED, s)
    else:
        m.atom_str(TYPE_STRING, s)

marshal_w__Rope = marshal_w__String

def unmarshal_String(space, u, tc):
    return space.wrap(u.get_str())
register(TYPE_STRING, unmarshal_String)

def unmarshal_interned(space, u, tc):
    w_ret = space.wrap(u.get_str())
    u.stringtable_w.append(w_ret)
    w_intern = space.builtin.get('intern')
    space.call_function(w_intern, w_ret)
    return w_ret
register(TYPE_INTERNED, unmarshal_interned)

def unmarshal_stringref(space, u, tc):
    idx = u.get_int()
    try:
        return u.stringtable_w[idx]
    except IndexError:
        raise_exception(space, 'bad marshal data')
register(TYPE_STRINGREF, unmarshal_stringref)

def marshal_w__Tuple(space, w_tuple, m):
    items = w_tuple.wrappeditems
    m.put_tuple_w(TYPE_TUPLE, items)

def unmarshal_Tuple(space, u, tc):
    items_w = u.get_tuple_w()
    return space.newtuple(items_w)
register(TYPE_TUPLE, unmarshal_Tuple)

def marshal_w__List(space, w_list, m):
    items = w_list.wrappeditems[:]
    m.put_tuple_w(TYPE_LIST, items)

def unmarshal_List(space, u, tc):
    items_w = u.get_list_w()
    return space.newlist(items_w)

def finish_List(space, items_w, typecode):
    return space.newlist(items_w)
register(TYPE_LIST, unmarshal_List)

def marshal_w__DictMulti(space, w_dict, m):
    m.start(TYPE_DICT)
    for w_tuple in w_dict.items():
        w_key, w_value = space.fixedview(w_tuple, 2)
        m.put_w_obj(w_key)
        m.put_w_obj(w_value)
    m.atom(TYPE_NULL)

def unmarshal_DictMulti(space, u, tc):
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
register(TYPE_DICT, unmarshal_DictMulti)

def unmarshal_NULL(self, u, tc):
    return None
register(TYPE_NULL, unmarshal_NULL)

# this one is registered by hand:
def marshal_w_pycode(space, w_pycode, m):
    m.start(TYPE_CODE)
    # see pypy.interpreter.pycode for the layout
    x = space.interp_w(PyCode, w_pycode)
    m.put_int(x.co_argcount)
    m.put_int(x.co_nlocals)
    m.put_int(x.co_stacksize)
    m.put_int(x.co_flags)
    m.atom_str(TYPE_STRING, x.co_code)
    m.put_tuple_w(TYPE_TUPLE, x.co_consts_w[:])
    m.atom_strlist(TYPE_TUPLE, TYPE_INTERNED, [space.str_w(w_name) for w_name in x.co_names_w])
    m.atom_strlist(TYPE_TUPLE, TYPE_INTERNED, x.co_varnames)
    m.atom_strlist(TYPE_TUPLE, TYPE_INTERNED, x.co_freevars)
    m.atom_strlist(TYPE_TUPLE, TYPE_INTERNED, x.co_cellvars)
    m.atom_str(TYPE_INTERNED, x.co_filename)
    m.atom_str(TYPE_INTERNED, x.co_name)
    m.put_int(x.co_firstlineno)
    m.atom_str(TYPE_STRING, x.co_lnotab)

model.MM.marshal_w.register(marshal_w_pycode, PyCode)

# helper for unmarshalling string lists of code objects.
# unfortunately they now can be interned or referenced,
# so we no longer can handle it in interp_marshal.atom_strlist

def unmarshal_str(u):
    w_obj = u.get_w_obj()
    try:
        return u.space.str_w(w_obj)
    except OperationError, e:
        if e.match(u.space, u.space.w_TypeError):
            u.raise_exc('invalid marshal data for code object')
        else:
            raise

def unmarshal_strlist(u, tc):
    lng = u.atom_lng(tc)
    res = [None] * lng
    idx = 0
    space = u.space
    while idx < lng:
        res[idx] = unmarshal_str(u)
        idx += 1
    return res

def unmarshal_pycode(space, u, tc):
    argcount    = u.get_int()
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
    filename    = unmarshal_str(u)
    name        = unmarshal_str(u)
    firstlineno = u.get_int()
    lnotab      = unmarshal_str(u)
    code = PyCode(space, argcount, nlocals, stacksize, flags,
                  code, consts_w[:], names, varnames, filename,
                  name, firstlineno, lnotab, freevars, cellvars)
    return space.wrap(code)
register(TYPE_CODE, unmarshal_pycode)

def marshal_w__Unicode(space, w_unicode, m):
    s = unicodehelper.PyUnicode_EncodeUTF8(space, space.unicode_w(w_unicode))
    m.atom_str(TYPE_UNICODE, s)

def unmarshal_Unicode(space, u, tc):
    return space.wrap(unicodehelper.PyUnicode_DecodeUTF8(space, u.get_str()))
register(TYPE_UNICODE, unmarshal_Unicode)

app = gateway.applevel(r'''
    def tuple_to_set(datalist, frozen=False):
        if frozen:
            return frozenset(datalist)
        return set(datalist)
''')

tuple_to_set = app.interphook('tuple_to_set')

# not directly supported:
def marshal_w_set(space, w_set, m):
    # cannot access this list directly, because it's
    # type is not exactly known through applevel.
    lis_w = space.fixedview(w_set)
    m.put_tuple_w(TYPE_SET, lis_w)

handled_by_any.append( ('set', marshal_w_set) )

# not directly supported:
def marshal_w_frozenset(space, w_frozenset, m):
    lis_w = space.fixedview(w_frozenset)
    m.put_tuple_w(TYPE_FROZENSET, lis_w)

handled_by_any.append( ('frozenset', marshal_w_frozenset) )

def unmarshal_set_frozenset(space, u, tc):
    items_w = u.get_tuple_w()
    if tc == TYPE_SET:
        w_frozen = space.w_False
    else:
        w_frozen = space.w_True
    w_tup = space.newtuple(items_w)
    return tuple_to_set(space, w_tup, w_frozen)
register(TYPE_SET + TYPE_FROZENSET, unmarshal_set_frozenset)

# dispatching for all not directly dispatched types
def marshal_w__ANY(space, w_obj, m):
    w_type = space.type(w_obj)
    for name, func in handled_by_any:
        w_t = space.builtin.get(name)
        if space.is_true(space.issubtype(w_type, w_t)):
            func(space, w_obj, m)
            return

    # any unknown object implementing the buffer protocol is
    # accepted and encoded as a plain string
    try:
        s = space.bufferstr_w(w_obj)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        m.atom_str(TYPE_STRING, s)
        return

    raise_exception(space, "unmarshallable object")

register_all(vars())
