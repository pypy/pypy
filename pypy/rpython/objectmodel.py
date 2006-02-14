"""
This file defines utilities for manipulating objects in an
RPython-compliant way.
"""

class Symbolic(object):

    def annotation(self):
        return None

    def lltype(self):
        return None

import new
import weakref

def instantiate(cls):
    "Create an empty instance of 'cls'."
    if isinstance(cls, type):
        return object.__new__(cls)
    else:
        return new.instance(cls)

def we_are_translated():
    return False
# annotation -> True

def keepalive_until_here(*values):
    pass

def hint(x, **kwds):
    return x


class FREED_OBJECT(object):
    def __getattribute__(self, attr):
        raise RuntimeError("trying to access freed object")
    def __setattr__(self, attr, value):
        raise RuntimeError("trying to access freed object")


def free_non_gc_object(obj):
    assert not getattr(obj.__class__, "_alloc_flavor_", 'gc').startswith('gc'), "trying to free gc object"
    obj.__dict__ = {}
    obj.__class__ = FREED_OBJECT

# XXX these things don't clearly belong here XXX

# the obtained address will not keep the object alive. e.g. if the object is
# only reachable through an address, it might get collected
def cast_ptr_to_adr(obj):
    from pypy.rpython.memory.lltypesimulation import simulatorptr
    assert isinstance(obj, simulatorptr)
    return obj._address

def cast_adr_to_ptr(adr, EXPECTED_TYPE):
    from pypy.rpython.memory.lltypesimulation import simulatorptr
    return simulatorptr(EXPECTED_TYPE, adr)
   
# __ hlinvoke XXX this doesn't seem completely the right place for this

def hlinvoke(repr, llcallable, *args):
    raise TypeError, "hlinvoke is meant to be rtyped and not called direclty"

# generically insert ll ops

# xxx Another approach would combine a llop function with a factory of names

class LLOp(object):

    def __init__(self, opname):
        self.opname = opname

    __name__ = property(lambda self: 'llop_'+self.opname)

    def __call__(self, RESULTTYPE, *args):
        raise TypeError, "llop is meant to be rtyped and not called direclty"

    def compute_result_annotation(self, RESULTTYPE, *args):
        from pypy.annotation.model import lltype_to_annotation
        assert RESULTTYPE.is_constant()
        return lltype_to_annotation(RESULTTYPE.const)

    def specialize(self, hop):
        args_v = [hop.inputarg(r, i+1) for i, r in enumerate(hop.args_r[1:])]
        hop.exception_is_here()
        return hop.genop(self.opname, args_v, resulttype=hop.r_result.lowleveltype)

class LLOpFactory(object):
    def __init__(self):
        self._cache = {}
        
    def _freeze_(self):
        return True

    def __getattr__(self, opname):
        if opname == 'compute_result_annotation':
            raise AttributeError
        try:
            return self._cache[opname]
        except KeyError:
            llop = self._cache[opname] = LLOp(opname)
            return llop
        
llop = LLOpFactory()


# ____________________________________________________________


class r_dict(object):
    """An RPython dict-like object.
    Only provides the interface supported by RPython.
    The functions key_eq() and key_hash() are used by the key comparison
    algorithm."""

    def __init__(self, key_eq, key_hash):
        self._dict = {}
        self.key_eq = key_eq
        self.key_hash = key_hash

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
