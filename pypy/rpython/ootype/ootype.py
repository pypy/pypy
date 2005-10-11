import weakref, operator
import py
from pypy.rpython.rarithmetic import r_uint
from pypy.tool.uid import Hashable
from pypy.tool.tls import tlsobject
from types import NoneType

TLS = tlsobject()

def saferecursive(func, defl):
    def safe(*args):
        try:
            seeing = TLS.seeing
        except AttributeError:
            seeing = TLS.seeing = {}
        seeingkey = tuple([func] + [id(arg) for arg in args])
        if seeingkey in seeing:
            return defl
        seeing[seeingkey] = True
        try:
            return func(*args)
        finally:
            del seeing[seeingkey]
    return safe

#safe_equal = saferecursive(operator.eq, True)
def safe_equal(x, y):
    # a specialized version for performance
    try:
        seeing = TLS.seeing_eq
    except AttributeError:
        seeing = TLS.seeing_eq = {}
    seeingkey = (id(x), id(y))
    if seeingkey in seeing:
        return True
    seeing[seeingkey] = True
    try:
        return x == y
    finally:
        del seeing[seeingkey]


class frozendict(dict):

    def __hash__(self):
        items = self.items()
        items.sort()
        return hash(tuple(items))


class OOType(object):
    # the following line prevents '__cached_hash' to be in the __dict__ of
    # the instance, which is needed for __eq__() and __hash__() to work.
    __slots__ = ['__dict__', '__cached_hash']

    def __eq__(self, other):
        return self.__class__ is other.__class__ and (
            self is other or safe_equal(self.__dict__, other.__dict__))

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        # cannot use saferecursive() -- see test_lltype.test_hash().
        # NB. the __cached_hash should neither be used nor updated
        # if we enter with hash_level > 0, because the computed
        # __hash__ can be different in this situation.
        hash_level = 0
        try:
            hash_level = TLS.nested_hash_level
            if hash_level == 0:
                return self.__cached_hash
        except AttributeError:
            pass
        if hash_level >= 3:
            return 0
        items = self.__dict__.items()
        items.sort()
        TLS.nested_hash_level = hash_level + 1
        try:
            result = hash((self.__class__,) + tuple(items))
        finally:
            TLS.nested_hash_level = hash_level
        if hash_level == 0:
            self.__cached_hash = result
        return result

    # due to this dynamic hash value, we should forbid
    # pickling, until we have an algorithm for that.
    # but we just provide a tag for external help.
    __hash_is_not_constant__ = True

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return self.__class__.__name__

    def _short_name(self):
        return str(self)

    def _defl(self, parent=None, parentindex=None):
        raise NotImplementedError

    def _freeze_(self):
        return True

class Primitive(OOType):
    def __init__(self, name, default):
        self._name = self.__name__ = name
        self._default = default

    def __str__(self):
        return self._name

    def _defl(self, parent=None, parentindex=None):
        return self._default

    def _is_atomic(self):
        return True

    _example = _defl

Signed   = Primitive("Signed", 0)
Unsigned = Primitive("Unsigned", r_uint(0))
Float    = Primitive("Float", 0.0)
Char     = Primitive("Char", '\x00')
Bool     = Primitive("Bool", False)
Void     = Primitive("Void", None)
UniChar  = Primitive("UniChar", u'\x00')

class Class(OOType):

    def __init__(self, name, superclass, fields):
        self._fields = fields

        for name, defn in fields.iteritems():
            if type(defn) is not tuple:
                fields[name] = (defn, defn._defl())
            else:
                ootype, default = defn

                if ootype != typeOf(default):
                    raise TypeError("Expected type %r for default" % ootype)

# ____________________________________________________________

class _instance(object):
    
    def __init__(self, CLASS):
        self.__dict__["_TYPE"] = CLASS

        for name, (ootype, default) in self._TYPE._fields.iteritems():
            self.__dict__[name] = default

    def __getattr__(self, name):
        try:
            self._TYPE._fields[name]
        except KeyError:
            raise TypeError("No field named %r" % name)

        return self.__dict__[name]

    def __setattr__(self, name, value):
        self.__getattr__(name)
            
        if self._TYPE._fields[name][0] != typeOf(value):
            raise TypeError("Expected type %r" % self._TYPE._fields[name][0])

        self.__dict__[name] = value

class _null_instance(_instance):

    def __init__(self, CLASS):
        _instance.__init__(self, CLASS)

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
    
        _instance.__getattr__(self, name)
        
        raise RuntimeError("Access to field in null object")

    def __setattr__(self, name, value):
        _instance.__setattr__(self, name, value)

        raise RuntimeError("Assignment to field in null object")

def new(CLASS):
    return _instance(CLASS)

def null(CLASS):
    return _null_instance(CLASS)

def typeOf(val):
    try:
        return val._TYPE
    except AttributeError:
        tp = type(val)
        if tp is NoneType:
            return Void   # maybe
        if tp is int:
            return Signed
        if tp is bool:
            return Bool
        if tp is r_uint:
            return Unsigned
        if tp is float:
            return Float
        if tp is str:
            assert len(val) == 1
            return Char
        if tp is unicode:
            assert len(val) == 1
            return UniChar
        raise TypeError("typeOf(%r object)" % (tp.__name__,))

class InvalidCast(TypeError):
    pass


