"""
This file defines utilities for manipulating objects in an
RPython-compliant way.
"""

import sys
import types
import math

# specialize is a decorator factory for attaching _annspecialcase_
# attributes to functions: for example
#
# f._annspecialcase_ = 'specialize:memo' can be expressed with:
# @specialize.memo()
# def f(...
#
# f._annspecialcase_ = 'specialize:arg(0)' can be expressed with:
# @specialize.arg(0)
# def f(...
#

from pypy.rpython.extregistry import ExtRegistryEntry

class _Specialize(object):
    def memo(self):
        """ Specialize functions based on argument values. All arguments has
        to be constant at the compile time. The whole function call is replaced
        by a call result then.
        """
        def decorated_func(func):
            func._annspecialcase_ = 'specialize:memo'
            return func
        return decorated_func

    def arg(self, *args):
        """ Specialize function based on values of given positions of arguments.
        They must be compile-time constants in order to work.

        There will be a copy of provided function for each combination
        of given arguments on positions in args (that can lead to
        exponential behavior!).
        """
        def decorated_func(func):
            func._annspecialcase_ = 'specialize:arg' + self._wrap(args)
            return func

        return decorated_func

    def argtype(self, *args):
        """ Specialize function based on types of arguments on given positions.

        There will be a copy of provided function for each combination
        of given arguments on positions in args (that can lead to
        exponential behavior!).
        """
        def decorated_func(func):
            func._annspecialcase_ = 'specialize:argtype' + self._wrap(args)
            return func

        return decorated_func

    def ll(self):
        """ This is version of argtypes that cares about low-level types
        (so it'll get additional copies for two different types of pointers
        for example). Same warnings about exponential behavior apply.
        """
        def decorated_func(func):
            func._annspecialcase_ = 'specialize:ll'
            return func

        return decorated_func

    def ll_and_arg(self, *args):
        """ This is like ll(), but instead of specializing on all arguments,
        specializes on only the arguments at the given positions
        """
        def decorated_func(func):
            func._annspecialcase_ = 'specialize:ll_and_arg' + self._wrap(args)
            return func

        return decorated_func

    def _wrap(self, args):
        return "("+','.join([repr(arg) for arg in args]) +")"
        
specialize = _Specialize()

def enforceargs(*args):
    """ Decorate a function with forcing of RPython-level types on arguments.
    None means no enforcing.

    XXX shouldn't we also add asserts in function body?
    """
    def decorator(f):
        f._annenforceargs_ = args
        return f
    return decorator

# ____________________________________________________________

class Symbolic(object):

    def annotation(self):
        return None

    def lltype(self):
        return None

    def __cmp__(self, other):
        if self is other:
            return 0
        else:
            raise TypeError("Symbolics can not be compared!")

    def __hash__(self):
        raise TypeError("Symbolics are not hashable!")
    
    def __nonzero__(self):
        raise TypeError("Symbolics are not comparable")

class ComputedIntSymbolic(Symbolic):

    def __init__(self, compute_fn):
        self.compute_fn = compute_fn

    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger()

    def lltype(self):
        from pypy.rpython.lltypesystem import lltype
        return lltype.Signed

class CDefinedIntSymbolic(Symbolic):

    def __init__(self, expr, default=0):
        self.expr = expr
        self.default = default

    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger()

    def lltype(self):
        from pypy.rpython.lltypesystem import lltype
        return lltype.Signed
    
malloc_zero_filled = CDefinedIntSymbolic('MALLOC_ZERO_FILLED', default=0)
running_on_llinterp = CDefinedIntSymbolic('RUNNING_ON_LLINTERP', default=1)
# running_on_llinterp is meant to have the value 0 in all backends

# ____________________________________________________________

def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return cls.__new__(cls)
    else:
        return types.InstanceType(cls)

def we_are_translated():
    return False
# annotation -> True (replaced by the flow objspace)

def keepalive_until_here(*values):
    pass

# ____________________________________________________________

class FREED_OBJECT(object):
    def __getattribute__(self, attr):
        raise RuntimeError("trying to access freed object")
    def __setattr__(self, attr, value):
        raise RuntimeError("trying to access freed object")


def free_non_gc_object(obj):
    assert not getattr(obj.__class__, "_alloc_flavor_", 'gc').startswith('gc'), "trying to free gc object"
    obj.__dict__ = {}
    obj.__class__ = FREED_OBJECT

# ____________________________________________________________

def newlist(sizehint=0):
    """ Create a new list, but pass a hint how big the size should be
    preallocated
    """
    return []

class Entry(ExtRegistryEntry):
    _about_ = newlist

    def compute_result_annotation(self, s_sizehint):
        from pypy.annotation.model import SomeInteger
        
        assert isinstance(s_sizehint, SomeInteger)
        return self.bookkeeper.newlist()

    def specialize_call(self, orig_hop, i_sizehint=None):
        from pypy.rpython.rlist import rtype_newlist
        # fish a bit hop
        hop = orig_hop.copy()
        v = hop.args_v[0]
        r, s = hop.r_s_popfirstarg()
        if s.is_constant():
            v = hop.inputconst(r, s.const)
        hop.exception_is_here()
        return rtype_newlist(hop, v_sizehint=v)

# ____________________________________________________________
#
# id-like functions.  The idea is that calling hash() or id() is not
# allowed in RPython.  You have to call one of the following more
# precise functions.

def compute_hash(x):
    """RPython equivalent of hash(x), where 'x' is an immutable
    RPython-level.  For strings or unicodes it computes the hash as
    in Python.  For tuples it calls compute_hash() recursively.
    For instances it uses compute_identity_hash().

    Note that this can return 0 or -1 too.

    Behavior across translation:

      * on lltypesystem, it always returns the same number, both
        before and after translation.  Dictionaries don't need to
        be rehashed after translation.

      * on ootypesystem, the value changes because of translation.
        Dictionaries need to be rehashed.
    """
    if isinstance(x, (str, unicode)):
        return _hash_string(x)
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        return _hash_float(x)
    if isinstance(x, tuple):
        return _hash_tuple(x)
    if x is None:
        return 0
    return compute_identity_hash(x)

def compute_identity_hash(x):
    """RPython equivalent of object.__hash__(x).  This returns the
    so-called 'identity hash', which is the non-overridable default hash
    of Python.  Can be called for any RPython-level object that turns
    into a GC object, but not NULL.  The value is not guaranteed to be the
    same before and after translation, except for RPython instances on the
    lltypesystem.
    """
    assert x is not None
    result = object.__hash__(x)
    try:
        x.__dict__['__precomputed_identity_hash'] = result
    except (TypeError, AttributeError):
        pass
    return result

def compute_unique_id(x):
    """RPython equivalent of id(x).  The 'x' must be an RPython-level
    object that turns into a GC object.  This operation can be very
    costly depending on the garbage collector.  To remind you of this
    fact, we don't support id(x) directly.
    (XXX not implemented on ootype, falls back to compute_identity_hash)
    """
    return id(x)      # XXX need to return r_longlong on some platforms

def current_object_addr_as_int(x):
    """A cheap version of id(x).  The current memory location of an
    object can change over time for moving GCs.  Also note that on
    ootypesystem this typically doesn't return the real address but
    just the same as compute_hash(x).
    """
    from pypy.rlib.rarithmetic import intmask
    return intmask(id(x))

# ----------

def _hash_string(s):
    """The algorithm behind compute_hash() for a string or a unicode."""
    from pypy.rlib.rarithmetic import intmask
    length = len(s)
    if length == 0:
        return -1
    x = ord(s[0]) << 7
    i = 0
    while i < length:
        x = intmask((1000003*x) ^ ord(s[i]))
        i += 1
    x ^= length
    return intmask(x)

def _hash_float(f):
    """The algorithm behind compute_hash() for a float.
    This implementation is identical to the CPython implementation,
    except the fact that the integer case is not treated specially.
    In RPython, floats cannot be used with ints in dicts, anyway.
    """
    from pypy.rlib.rarithmetic import intmask
    from pypy.rlib.rfloat import isfinite, isinf
    if not isfinite(f):
        if isinf(f):
            if f < 0.0:
                return -271828
            else:
                return 314159
        else: #isnan(f):
            return 0
    v, expo = math.frexp(f)
    v *= TAKE_NEXT
    hipart = int(v)
    v = (v - float(hipart)) * TAKE_NEXT
    x = hipart + int(v) + (expo << 15)
    return intmask(x)
TAKE_NEXT = float(2**31)

def _hash_tuple(t):
    """NOT_RPYTHON.  The algorithm behind compute_hash() for a tuple.
    It is modelled after the old algorithm of Python 2.3, which is
    a bit faster than the one introduced by Python 2.4.  We assume
    that nested tuples are very uncommon in RPython, making the bad
    case unlikely.
    """
    from pypy.rlib.rarithmetic import intmask
    x = 0x345678
    for item in t:
        y = compute_hash(item)
        x = intmask((1000003 * x) ^ y)
    return x

# ----------

class Entry(ExtRegistryEntry):
    _about_ = compute_hash

    def compute_result_annotation(self, s_x):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        r_obj, = hop.args_r
        v_obj, = hop.inputargs(r_obj)
        ll_fn = r_obj.get_ll_hash_function()
        return hop.gendirectcall(ll_fn, v_obj)

class Entry(ExtRegistryEntry):
    _about_ = compute_identity_hash

    def compute_result_annotation(self, s_x):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        vobj, = hop.inputargs(hop.args_r[0])
        if hop.rtyper.type_system.name == 'lltypesystem':
            ok = (isinstance(vobj.concretetype, lltype.Ptr) and
                  vobj.concretetype.TO._gckind == 'gc')
        else:
            from pypy.rpython.ootypesystem import ootype
            ok = isinstance(vobj.concretetype, ootype.OOType)
        if not ok:
            from pypy.rpython.error import TyperError
            raise TyperError("compute_identity_hash() cannot be applied to"
                             " %r" % (vobj.concretetype,))
        return hop.genop('gc_identityhash', [vobj], resulttype=lltype.Signed)

class Entry(ExtRegistryEntry):
    _about_ = compute_unique_id

    def compute_result_annotation(self, s_x):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        vobj, = hop.inputargs(hop.args_r[0])
        if hop.rtyper.type_system.name == 'lltypesystem':
            ok = (isinstance(vobj.concretetype, lltype.Ptr) and
                  vobj.concretetype.TO._gckind == 'gc')
        else:
            from pypy.rpython.ootypesystem import ootype
            ok = isinstance(vobj.concretetype, ootype.Instance)
        if not ok:
            from pypy.rpython.error import TyperError
            raise TyperError("compute_unique_id() cannot be applied to"
                             " %r" % (vobj.concretetype,))
        return hop.genop('gc_id', [vobj], resulttype=lltype.Signed)

class Entry(ExtRegistryEntry):
    _about_ = current_object_addr_as_int

    def compute_result_annotation(self, s_x):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger()

    def specialize_call(self, hop):
        vobj, = hop.inputargs(hop.args_r[0])
        if hop.rtyper.type_system.name == 'lltypesystem':
            from pypy.rpython.lltypesystem import lltype
            if isinstance(vobj.concretetype, lltype.Ptr):
                return hop.genop('cast_ptr_to_int', [vobj],
                                 resulttype = lltype.Signed)
        elif hop.rtyper.type_system.name == 'ootypesystem':
            from pypy.rpython.ootypesystem import ootype
            if isinstance(vobj.concretetype, ootype.Instance):
                return hop.genop('gc_identityhash', [vobj],
                                 resulttype = ootype.Signed)
        from pypy.rpython.error import TyperError
        raise TyperError("current_object_addr_as_int() cannot be applied to"
                         " %r" % (vobj.concretetype,))

# ____________________________________________________________

def hlinvoke(repr, llcallable, *args):
    raise TypeError, "hlinvoke is meant to be rtyped and not called direclty"

def invoke_around_extcall(before, after):
    """Call before() before any external function call, and after() after.
    At the moment only one pair before()/after() can be registered at a time.
    """
    # NOTE: the hooks are cleared during translation!  To be effective
    # in a compiled program they must be set at run-time.
    from pypy.rpython.lltypesystem import rffi
    rffi.aroundstate.before = before
    rffi.aroundstate.after = after
    # the 'aroundstate' contains regular function and not ll pointers to them,
    # but let's call llhelper() anyway to force their annotation
    from pypy.rpython.annlowlevel import llhelper
    llhelper(rffi.AroundFnPtr, before)
    llhelper(rffi.AroundFnPtr, after)

def is_in_callback():
    from pypy.rpython.lltypesystem import rffi
    return rffi.stackcounter.stacks_counter > 1


class UnboxedValue(object):
    """A mixin class to use for classes that have exactly one field which
    is an integer.  They are represented as a tagged pointer, if the
    translation.taggedpointers config option is used."""
    _mixin_ = True

    def __new__(cls, value):
        assert '__init__' not in cls.__dict__  # won't be called anyway
        assert isinstance(cls.__slots__, str) or len(cls.__slots__) == 1
        return super(UnboxedValue, cls).__new__(cls)

    def __init__(self, value):
        # this funtion is annotated but not included in the translated program
        int_as_pointer = value * 2 + 1   # XXX for now
        if -sys.maxint-1 <= int_as_pointer <= sys.maxint:
            if isinstance(self.__class__.__slots__, str):
                setattr(self, self.__class__.__slots__, value)
            else:
                setattr(self, self.__class__.__slots__[0], value)
        else:
            raise OverflowError("UnboxedValue: argument out of range")

    def __repr__(self):
        return '<unboxed %d>' % (self.get_untagged_value(),)

    def get_untagged_value(self):   # helper, equivalent to reading the custom field
        if isinstance(self.__class__.__slots__, str):
            return getattr(self, self.__class__.__slots__)
        else:
            return getattr(self, self.__class__.__slots__[0])

# ____________________________________________________________


class r_dict(object):
    """An RPython dict-like object.
    Only provides the interface supported by RPython.
    The functions key_eq() and key_hash() are used by the key comparison
    algorithm."""

    def __init__(self, key_eq, key_hash, force_non_null=False):
        self._dict = {}
        self.key_eq = key_eq
        self.key_hash = key_hash
        self.force_non_null = force_non_null

    def __getitem__(self, key):
        return self._dict[_r_dictkey(self, key)]

    def __setitem__(self, key, value):
        self._dict[_r_dictkey(self, key)] = value

    def __delitem__(self, key):
        del self._dict[_r_dictkey(self, key)]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        for dk in self._dict:
            yield dk.key

    def __contains__(self, key):
        return _r_dictkey(self, key) in self._dict

    def get(self, key, default):
        return self._dict.get(_r_dictkey(self, key), default)

    def setdefault(self, key, default):
        return self._dict.setdefault(_r_dictkey(self, key), default)

    def popitem(self):
        dk, value = self._dict.popitem()
        return dk.key, value

    def copy(self):
        result = r_dict(self.key_eq, self.key_hash)
        result.update(self)
        return result

    def update(self, other):
        for key, value in other.items():
            self[key] = value

    def keys(self):
        return [dk.key for dk in self._dict]

    def values(self):
        return self._dict.values()

    def items(self):
        return [(dk.key, value) for dk, value in self._dict.items()]

    iterkeys = __iter__

    def itervalues(self):
        return self._dict.itervalues()

    def iteritems(self):
        for dk, value in self._dict.items():
            yield dk.key, value

    def clear(self):
        self._dict.clear()

    def __repr__(self):
        "Representation for debugging purposes."
        return 'r_dict(%r)' % (self._dict,)

    def __hash__(self):
        raise TypeError("cannot hash r_dict instances")


class _r_dictkey(object):
    __slots__ = ['dic', 'key', 'hash']
    def __init__(self, dic, key):
        self.dic = dic
        self.key = key
        self.hash = dic.key_hash(key)
    def __eq__(self, other):
        if not isinstance(other, _r_dictkey):
            return NotImplemented
        return self.dic.key_eq(self.key, other.key)
    def __ne__(self, other):
        if not isinstance(other, _r_dictkey):
            return NotImplemented
        return not self.dic.key_eq(self.key, other.key)
    def __hash__(self):
        return self.hash

    def __repr__(self):
        return repr(self.key)

class _r_dictkey_with_hash(_r_dictkey):
    def __init__(self, dic, key, hash):
        self.dic = dic
        self.key = key
        self.hash = hash
