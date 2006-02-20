import py
from pypy.rpython.rarithmetic import r_uint, r_ulonglong, r_longlong
from pypy.rpython.objectmodel import Symbolic
from pypy.tool.uid import Hashable
from pypy.tool.tls import tlsobject
from pypy.tool.picklesupport import getstate_with_slots, setstate_with_slots, pickleable_weakref
from types import NoneType
from sys import maxint

log = py.log.Producer('lltype')

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


class LowLevelType(object):
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

    def _inline_is_varsize(self, last):
        return False

    def _is_atomic(self):
        return False

    def _is_varsize(self):
        return False

    __getstate__ = getstate_with_slots
    __setstate__ = setstate_with_slots

NFOUND = object()

class ContainerType(LowLevelType):
    _adtmeths = {}

    def _gcstatus(self):
        return isinstance(self, GC_CONTAINER)

    def _inline_is_varsize(self, last):
        raise TypeError, "%r cannot be inlined in structure" % self

    def _install_extras(self, adtmeths={}, hints={}):
        self._adtmeths = frozendict(adtmeths)
        self._hints = frozendict(hints)

    def __getattr__(self, name):
        adtmeth = self._adtmeths.get(name, NFOUND)
        if adtmeth is not NFOUND:
            if getattr(adtmeth, '_type_method', False):
                return adtmeth.__get__(self)
            else:
                return adtmeth
        self._nofield(name)

    def _nofield(self, name):
        raise AttributeError("no field %r" % name)
        

class Struct(ContainerType):
    def __init__(self, name, *fields, **kwds):
        self._name = self.__name__ = name
        flds = {}
        names = []
        self._arrayfld = None
        for name, typ in fields:
            if name.startswith('_'):
                raise NameError, ("%s: field name %r should not start with "
                                  "an underscore" % (self._name, name,))
            names.append(name)
            if name in flds:
                raise TypeError("%s: repeated field name" % self._name)
            flds[name] = typ
            if isinstance(typ, GC_CONTAINER):
                if name == fields[0][0] and isinstance(self, GC_CONTAINER):
                    pass  # can inline a GC_CONTAINER as 1st field of GcStruct
                else:
                    raise TypeError("%s: cannot inline GC container %r" % (
                        self._name, typ))

        # look if we have an inlined variable-sized array as the last field
        if fields:
            for name, typ in fields[:-1]:
                typ._inline_is_varsize(False)
                first = False
            name, typ = fields[-1]
            if typ._inline_is_varsize(True):
                self._arrayfld = name
        self._flds = frozendict(flds)
        self._names = tuple(names)

        self._install_extras(**kwds)

    def _first_struct(self):
        if self._names:
            first = self._names[0]
            FIRSTTYPE = self._flds[first]
            if isinstance(FIRSTTYPE, Struct) and self._gcstatus() == FIRSTTYPE._gcstatus():
                return first, FIRSTTYPE
        return None, None

    def _inline_is_varsize(self, last):
        if self._arrayfld:
            raise TypeError("cannot inline a var-sized struct "
                            "inside another container")
        return False

    def _is_atomic(self):
        for typ in self._flds.values():
            if not typ._is_atomic():
                return False
        return True

    def _is_varsize(self):
        return self._arrayfld is not None

    def __getattr__(self, name):
        try:
            return self._flds[name]
        except KeyError:
            return ContainerType.__getattr__(self, name)


    def _nofield(self, name):
        raise AttributeError, 'struct %s has no field %r' % (self._name,
                                                             name)

    def _names_without_voids(self):
        names_without_voids = [name for name in self._names if self._flds[name] is not Void]
        return names_without_voids
    
    def _str_fields_without_voids(self):
        return ', '.join(['%s: %s' % (name, self._flds[name])
                          for name in self._names_without_voids(False)])
    _str_fields_without_voids = saferecursive(_str_fields_without_voids, '...')

    def _str_without_voids(self):
        return "%s %s { %s }" % (self.__class__.__name__,
                                 self._name, self._str_fields_without_voids())

    def _str_fields(self):
        return ', '.join(['%s: %s' % (name, self._flds[name])
                          for name in self._names])
    _str_fields = saferecursive(_str_fields, '...')

    def __str__(self):
        return "%s %s { %s }" % (self.__class__.__name__,
                                 self._name, self._str_fields())

    def _short_name(self):
        return "%s %s" % (self.__class__.__name__, self._name)

    def _defl(self, parent=None, parentindex=None):
        return _struct(self, parent=parent, parentindex=parentindex)

    def _container_example(self):
        if self._arrayfld is None:
            n = None
        else:
            n = 1
        return _struct(self, n)

class GcStruct(Struct):
    _runtime_type_info = None

    def _attach_runtime_type_info_funcptr(self, funcptr, destrptr):
        if self._runtime_type_info is None:
            self._runtime_type_info = opaqueptr(RuntimeTypeInfo, name=self._name, about=self)._obj
        if funcptr is not None:
            T = typeOf(funcptr)
            if (not isinstance(T, Ptr) or
                not isinstance(T.TO, FuncType) or
                len(T.TO.ARGS) != 1 or
                T.TO.RESULT != Ptr(RuntimeTypeInfo) or
                castable(T.TO.ARGS[0], Ptr(self)) < 0):
                raise TypeError("expected a runtime type info function "
                                "implementation, got: %s" % funcptr)
            self._runtime_type_info.query_funcptr = funcptr
        if destrptr is not None :
            T = typeOf(destrptr)
            if (not isinstance(T, Ptr) or
                not isinstance(T.TO, FuncType) or
                len(T.TO.ARGS) != 1 or
                T.TO.RESULT != Void or
                castable(T.TO.ARGS[0], Ptr(self)) < 0):
                raise TypeError("expected a destructor function "
                                "implementation, got: %s" % destrptr)
            self._runtime_type_info.destructor_funcptr = destrptr
           

class Array(ContainerType):
    __name__ = 'array'
    _anonym_struct = False
    
    def __init__(self, *fields, **kwds):
        if len(fields) == 1 and isinstance(fields[0], LowLevelType):
            self.OF = fields[0]
        else:
            self.OF = Struct("<arrayitem>", *fields)
            self._anonym_struct = True
        if isinstance(self.OF, GcStruct):
            raise TypeError("cannot have a GC structure as array item type")
        self.OF._inline_is_varsize(False)

        self._install_extras(**kwds)

    def _inline_is_varsize(self, last):
        if not last:
            raise TypeError("cannot inline an array in another container"
                            " unless as the last field of a structure")
        return True

    def _is_atomic(self):
        return self.OF._is_atomic()

    def _is_varsize(self):
        return True

    def _str_fields(self):
        if isinstance(self.OF, Struct):
            of = self.OF
            if self._anonym_struct:
                return "{ %s }" % of._str_fields()
            else:
                return "%s { %s }" % (of._name, of._str_fields())
        else:
            return str(self.OF)
    _str_fields = saferecursive(_str_fields, '...')

    def __str__(self):
        return "%s of %s " % (self.__class__.__name__,
                               self._str_fields(),)

    def _short_name(self):
        return "%s %s" % (self.__class__.__name__,
                          self.OF._short_name(),)
    _short_name = saferecursive(_short_name, '...')

    def _container_example(self):
        return _array(self, 1)

class GcArray(Array):
    def _inline_is_varsize(self, last):
        raise TypeError("cannot inline a GC array inside a structure")

class FuncType(ContainerType):
    __name__ = 'func'
    def __init__(self, args, result):
        for arg in args:
            assert isinstance(arg, LowLevelType)
            if isinstance(arg, ContainerType):
                raise TypeError, "function arguments can only be primitives or pointers"
        self.ARGS = tuple(args)
        assert isinstance(result, LowLevelType)
        if isinstance(result, ContainerType):
            raise TypeError, "function result can only be primitive or pointer"
        self.RESULT = result

    def __str__(self):
        args = ', '.join(map(str, self.ARGS))
        return "Func ( %s ) -> %s" % (args, self.RESULT)
    __str__ = saferecursive(__str__, '...')

    def _short_name(self):        
        args = ', '.join([ARG._short_name() for ARG in self.ARGS])
        return "Func(%s)->%s" % (args, self.RESULT._short_name())        
    _short_name = saferecursive(_short_name, '...')

    def _container_example(self):
        def ex(*args):
            return self.RESULT._defl()
        return _func(self, _callable=ex)

    def _trueargs(self):
        return [arg for arg in self.ARGS if arg is not Void]


class OpaqueType(ContainerType):
    
    def __init__(self, tag):
        self.tag = tag
        self.__name__ = tag

    def __str__(self):
        return "%s (opaque)" % self.tag

    def _inline_is_varsize(self, last):
        return False    # OpaqueType can be inlined

    def _container_example(self):
        return _opaque(self)

    def _defl(self, parent=None, parentindex=None):
        return _opaque(self, parent=parent, parentindex=parentindex)

RuntimeTypeInfo = OpaqueType("RuntimeTypeInfo")

class PyObjectType(ContainerType):
    __name__ = 'PyObject'
    def __str__(self):
        return "PyObject"
PyObject = PyObjectType()

class ForwardReference(ContainerType):
    def become(self, realcontainertype):
        if not isinstance(realcontainertype, ContainerType):
            raise TypeError("ForwardReference can only be to a container, "
                            "not %r" % (realcontainertype,))
        self.__class__ = realcontainertype.__class__
        self.__dict__ = realcontainertype.__dict__

    def __hash__(self):
        raise TypeError("%r object is not hashable" % self.__class__.__name__)

class GcForwardReference(ForwardReference):
    def become(self, realcontainertype):
        if not isinstance(realcontainertype, GC_CONTAINER):
            raise TypeError("GcForwardReference can only be to GcStruct or "
                            "GcArray, not %r" % (realcontainertype,))
        self.__class__ = realcontainertype.__class__
        self.__dict__ = realcontainertype.__dict__

GC_CONTAINER = (GcStruct, GcArray, PyObjectType, GcForwardReference)


class Primitive(LowLevelType):
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
if maxint == 2**31-1:
    SignedLongLong = Primitive("SignedLongLong", r_longlong(0))
    UnsignedLongLong = Primitive("UnsignedLongLong", r_ulonglong(0))
else:
    SignedLongLong = Signed
    UnsignedLongLong = Unsigned
Float    = Primitive("Float", 0.0)
Char     = Primitive("Char", '\x00')
Bool     = Primitive("Bool", False)
Void     = Primitive("Void", None)
UniChar  = Primitive("UniChar", u'\x00')


class Ptr(LowLevelType):
    __name__ = property(lambda self: '%sPtr' % self.TO.__name__)

    def __init__(self, TO):
        if not isinstance(TO, ContainerType):
            raise TypeError, ("can only point to a Container type, "
                              "not to %s" % (TO,))
        self.TO = TO

    def _needsgc(self):
        return self.TO._gcstatus()

    def __str__(self):
        return '* %s' % (self.TO, )
    
    def _short_name(self):
        return 'Ptr %s' % (self.TO._short_name(), )
    
    def _is_atomic(self):
        return not self.TO._gcstatus()

    def _defl(self, parent=None, parentindex=None):
        return _ptr(self, None)

    def _example(self):
        o = self.TO._container_example()
        return _ptr(self, o, solid=True)


# ____________________________________________________________


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
        if tp is r_ulonglong:
            return UnsignedLongLong
        if tp is r_longlong:
            return SignedLongLong
        if tp is float:
            return Float
        if tp is str:
            assert len(val) == 1
            return Char
        if tp is unicode:
            assert len(val) == 1
            return UniChar
        if issubclass(tp, Symbolic):
            return val.lltype()
        raise TypeError("typeOf(%r object)" % (tp.__name__,))

_to_primitive = {
    Signed: int,
    Unsigned: r_uint,
    Float: float,
    Char: chr,
    UniChar: unichr,
    Bool: bool,
}

def cast_primitive(TGT, value):
    ORIG = typeOf(value)
    if not isinstance(TGT, Primitive) or not isinstance(ORIG, Primitive):
        raise TypeError, "can only primitive to primitive"
    if ORIG == TGT:
        return value
    if ORIG == Char or ORIG == UniChar:
        value = ord(value)
    elif ORIG == Float:
        value = long(value)
    cast = _to_primitive.get(TGT)
    if cast is None:
        raise TypeError, "unsupported cast"
    return cast(value)
 

class InvalidCast(TypeError):
    pass

def _castdepth(OUTSIDE, INSIDE):
    if OUTSIDE == INSIDE:
        return 0
    dwn = 0
    while True:
        first, FIRSTTYPE = OUTSIDE._first_struct()
        if first is None:
            return -1
        dwn += 1
        if FIRSTTYPE == INSIDE:
            return dwn
        OUTSIDE = getattr(OUTSIDE, first)
 
def castable(PTRTYPE, CURTYPE):
    if CURTYPE._needsgc() != PTRTYPE._needsgc():
        raise TypeError("cast_pointer() cannot change the gc status: %s to %s"
                        % (CURTYPE, PTRTYPE))
    if (not isinstance(CURTYPE.TO, Struct) or
        not isinstance(PTRTYPE.TO, Struct)):
        raise InvalidCast(CURTYPE, PTRTYPE)
    CURSTRUC = CURTYPE.TO
    PTRSTRUC = PTRTYPE.TO
    d = _castdepth(CURSTRUC, PTRSTRUC)
    if d >= 0:
        return d
    u = _castdepth(PTRSTRUC, CURSTRUC)
    if u == -1:
        raise InvalidCast(CURTYPE, PTRTYPE)
    return -u

def cast_pointer(PTRTYPE, ptr):
    if not isinstance(ptr, _ptr) or not isinstance(PTRTYPE, Ptr):
        raise TypeError, "can only cast pointers to other pointers"
    CURTYPE = ptr._TYPE
    down_or_up = castable(PTRTYPE, CURTYPE)
    if down_or_up == 0:
        return ptr
    if not ptr: # null pointer cast
        return PTRTYPE._defl()
    if down_or_up > 0:
        p = ptr
        while down_or_up:
            p = getattr(p, typeOf(p).TO._names[0])
            down_or_up -= 1
        return _ptr(PTRTYPE, p._obj)
    u = -down_or_up
    struc = ptr._obj
    while u:
        parent = struc._parentstructure()
        if parent is None:
            raise RuntimeError("widening to trash: %r" % ptr)
        PARENTTYPE = struc._parent_type
        if getattr(parent, PARENTTYPE._names[0]) is not struc:
            raise InvalidCast(CURTYPE, PTRTYPE) # xxx different exception perhaps?
        struc = parent
        u -= 1
    if PARENTTYPE != PTRTYPE.TO:
        raise TypeError("widening %r inside %r instead of %r" % (CURTYPE, PARENTTYPE, PTRTYPE.TO))
    return _ptr(PTRTYPE, struc)

def _expose(val):
    """XXX A nice docstring here"""
    T = typeOf(val)
    if isinstance(T, ContainerType):
        val = _ptr(Ptr(T), val)
    return val

def parentlink(container):
    parent = container._parentstructure()
    if parent is not None:
        return parent, container._parent_index
##        if isinstance(parent, _struct):
##            for name in parent._TYPE._names:
##                if getattr(parent, name) is container:
##                    return parent, name
##            raise RuntimeError("lost ourselves")
##        if isinstance(parent, _array):
##            raise TypeError("cannot fish a pointer to an array item or an "
##                            "inlined substructure of it")
##        raise AssertionError("don't know about %r" % (parent,))
    else:
        return None, None


class _ptr(object):
    __slots__ = ('_TYPE', '_T', 
                 '_weak', '_solid',
                 '_obj0', '__weakref__')

    def _set_TYPE(self, TYPE):
        _ptr._TYPE.__set__(self, TYPE)

    def _set_T(self, T):
        _ptr._T.__set__(self, T)

    def _set_weak(self, weak):
        _ptr._weak.__set__(self, weak)

    def _set_solid(self, solid):
        _ptr._solid.__set__(self, solid)

    def _set_obj0(self, obj):
        _ptr._obj0.__set__(self, obj)

    def _needsgc(self):
        return self._TYPE._needsgc() # xxx other rules?

    def __init__(self, TYPE, pointing_to, solid=False):
        self._set_TYPE(TYPE)
        self._set_T(TYPE.TO)
        self._set_weak(False)
        self._setobj(pointing_to, solid)

    def _become(self, other):
        assert self._TYPE == other._TYPE
        assert not self._weak
        self._setobj(other._obj, other._solid)

    def __eq__(self, other):
        if not isinstance(other, _ptr):
            raise TypeError("comparing pointer with %r object" % (
                type(other).__name__,))
        if self._TYPE != other._TYPE:
            raise TypeError("comparing %r and %r" % (self._TYPE, other._TYPE))
        return self._obj == other._obj

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        raise TypeError("pointer objects are not hashable")

    def __nonzero__(self):
        return self._obj is not None

    # _setobj, _getobj and _obj0 are really _internal_ implementations details of _ptr,
    # use _obj if necessary instead !
    def _setobj(self, pointing_to, solid=False):        
        if pointing_to is None:
            obj0 = None
        elif solid or isinstance(self._T, (GC_CONTAINER, FuncType)):
            obj0 = pointing_to
        else:
            self._set_weak(True)
            obj0 = pickleable_weakref(pointing_to)
        self._set_solid(solid)
        self._set_obj0(obj0)
        
    def _getobj(self):
        obj = self._obj0
        if obj is not None and self._weak:
            obj = obj()
            if obj is None:
                raise RuntimeError("accessing already garbage collected %r"
                                   % (self._T,))                
            obj._check()
        return obj
    _obj = property(_getobj)

    def __getattr__(self, field_name): # ! can only return basic or ptr !
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                o = getattr(self._obj, field_name)
                return _expose(o)
        if isinstance(self._T, ContainerType):
            adtmeth = self._T._adtmeths.get(field_name)
            if adtmeth is not None:
                return adtmeth.__get__(self)
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    #def _setfirst(self, p):
    #    if isinstance(self._T, Struct) and self._T._names:
    #        if not isinstance(p, _ptr) or not isinstance(p._obj, _struct):
    #            raise InvalidCast(typeOf(p), typeOf(self))
    #        field_name = self._T._names[0]
    #        T1 = self._T._flds[field_name]
    #        T2 = typeOf(p._obj)
    #        if T1 != T2:
    #            raise InvalidCast(typeOf(p), typeOf(self))
    #        setattr(self._obj, field_name, p._obj)
    #        p._obj._setparentstructure(self._obj, 0)
    #        return
    #    raise TypeError("%r instance has no first field" % (self._T,))

    def __setattr__(self, field_name, val):
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                T1 = self._T._flds[field_name]
                T2 = typeOf(val)
                if T1 == T2:
                    setattr(self._obj, field_name, val)
                else:
                    raise TypeError("%r instance field %r:\n"
                                    "expects %r\n"
                                    "    got %r" % (self._T, field_name, T1, T2))
                return
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    def __getitem__(self, i): # ! can only return basic or ptr !
        if isinstance(self._T, Array):
            if not (0 <= i < len(self._obj.items)):
                raise IndexError("array index out of bounds")
            o = self._obj.items[i]
            return _expose(o)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __setitem__(self, i, val):
        if isinstance(self._T, Array):
            T1 = self._T.OF
            if isinstance(T1, ContainerType):
                raise TypeError("cannot directly assign to container array items")
            T2 = typeOf(val)
            if T2 != T1:
                    raise TypeError("%r items:\n"
                                    "expect %r\n"
                                    "   got %r" % (self._T, T1, T2))                
            if not (0 <= i < len(self._obj.items)):
                raise IndexError("array index out of bounds")
            self._obj.items[i] = val
            return
        raise TypeError("%r instance is not an array" % (self._T,))

    def __len__(self):
        if isinstance(self._T, Array):
            return len(self._obj.items)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '* %s' % (self._obj, )

    def __call__(self, *args):
        if isinstance(self._T, FuncType):
            if len(args) != len(self._T.ARGS):
                raise TypeError,"calling %r with wrong argument number: %r" % (self._T, args)
            for a, ARG in zip(args, self._T.ARGS):
                if typeOf(a) != ARG:
                    raise TypeError,"calling %r with wrong argument types: %r" % (self._T, args)
            callb = self._obj._callable
            if callb is None:
                raise RuntimeError,"calling undefined function"
            return callb(*args)
        raise TypeError("%r instance is not a function" % (self._T,))

    __getstate__ = getstate_with_slots
    __setstate__ = setstate_with_slots

assert not '__dict__' in dir(_ptr)

class _parentable(object):
    _kind = "?"

    __slots__ = ('_TYPE',
                 '_parent_type', '_parent_index', '_keepparent',
                 '_wrparent',
                 '__weakref__')

    def __init__(self, TYPE):
        self._wrparent = None
        self._TYPE = TYPE

    def _setparentstructure(self, parent, parentindex):
        self._wrparent = pickleable_weakref(parent)
        self._parent_type = typeOf(parent)
        self._parent_index = parentindex
        if (isinstance(self._parent_type, Struct)
            and parentindex == self._parent_type._names[0]
            and self._TYPE._gcstatus() == typeOf(parent)._gcstatus()):
            # keep strong reference to parent, we share the same allocation
            self._keepparent = parent 

    def _parentstructure(self):
        if self._wrparent is not None:
            parent = self._wrparent()
            if parent is None:
                raise RuntimeError("accessing sub%s %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self._kind, self, self._parent_type))
            parent._check()
            return parent
        return None

    def _check(self):
        self._parentstructure()

    __getstate__ = getstate_with_slots
    __setstate__ = setstate_with_slots

def _struct_variety(flds, cache={}):
    flds = list(flds)
    flds.sort()
    tag = tuple(flds)
    try:
        return cache[tag]
    except KeyError:
        class _struct1(_struct):
            __slots__ = flds
        cache[tag] = _struct1
        return _struct1
 
#for pickling support:
def _get_empty_instance_of_struct_variety(flds):
    cls = _struct_variety(flds)
    return object.__new__(cls)

class _struct(_parentable):
    _kind = "structure"

    __slots__ = ()

    def __new__(self, TYPE, n=None, parent=None, parentindex=None):
        my_variety = _struct_variety(TYPE._names)
        return object.__new__(my_variety)

    def __init__(self, TYPE, n=None, parent=None, parentindex=None):
        _parentable.__init__(self, TYPE)
        if n is not None and TYPE._arrayfld is None:
            raise TypeError("%r is not variable-sized" % (TYPE,))
        if n is None and TYPE._arrayfld is not None:
            raise TypeError("%r is variable-sized" % (TYPE,))
        for fld, typ in TYPE._flds.items():
            if fld == TYPE._arrayfld:
                value = _array(typ, n, parent=self, parentindex=fld)
            else:
                value = typ._defl(parent=self, parentindex=fld)
            setattr(self, fld, value)
        if parent is not None:
            self._setparentstructure(parent, parentindex)

    def __repr__(self):
        return '<%s>' % (self,)

    def _str_fields(self):
        fields = []
        for name in self._TYPE._names:
            T = self._TYPE._flds[name]
            if isinstance(T, Primitive):
                reprvalue = repr(getattr(self, name))
            else:
                reprvalue = '...'
            fields.append('%s=%s' % (name, reprvalue))
        return ', '.join(fields)

    def __str__(self):
        return 'struct %s { %s }' % (self._TYPE._name, self._str_fields())

    def __reduce__(self):
        return _get_empty_instance_of_struct_variety, (self.__slots__, ), getstate_with_slots(self) 

    __setstate__ = setstate_with_slots

class _array(_parentable):
    _kind = "array"

    __slots__ = ('items',)

    def __init__(self, TYPE, n, parent=None, parentindex=None):
        if not isinstance(n, int):
            raise TypeError, "array length must be an int"
        if n < 0:
            raise ValueError, "negative array length"
        _parentable.__init__(self, TYPE)
        self.items = [TYPE.OF._defl(parent=self, parentindex=j)
                      for j in range(n)]
        if parent is not None:
            self._setparentstructure(parent, parentindex)

    def __repr__(self):
        return '<%s>' % (self,)

    def _str_item(self, item):
        if isinstance(self._TYPE.OF, Struct):
            of = self._TYPE.OF
            if self._TYPE._anonym_struct:
                return "{%s}" % item._str_fields()
            else:
                return "%s {%s}" % (of._name, item._str_fields())
        else:
            return repr(item)

    def __str__(self):
        return 'array [ %s ]' % (', '.join([self._str_item(item)
                                            for item in self.items]),)

assert not '__dict__' in dir(_array)
assert not '__dict__' in dir(_struct)


class _func(object):
    def __init__(self, TYPE, **attrs):
        self._TYPE = TYPE
        self._name = "?"
        self._callable = None
        self.__dict__.update(attrs)

    def _parentstructure(self):
        return None

    def _check(self):
        pass

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "fn %s" % self._name

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(frozendict(self.__dict__))

    def __getstate__(self):
        import pickle, types
        __dict__ = self.__dict__.copy()
        try:
            pickle.dumps(self._callable)
        except pickle.PicklingError:
            __dict__['_callable'] = None
        return __dict__

    def __setstate__(self, __dict__):
        import new
        self.__dict__ = __dict__

class _opaque(_parentable):
    def __init__(self, TYPE, parent=None, parentindex=None, **attrs):
        _parentable.__init__(self, TYPE)
        self._name = "?"
        self.__dict__.update(attrs)
        if parent is not None:
            self._setparentstructure(parent, parentindex)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "%s %s" % (self._TYPE.__name__, self._name)


class _pyobject(Hashable):
    __slots__ = []   # or we get in trouble with pickling

    _TYPE = PyObject

    def _parentstructure(self):
        return None

    def _check(self):
        pass

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "pyobject %s" % (super(_pyobject, self).__str__(),)


def malloc(T, n=None, flavor='gc', immortal=False):
    if isinstance(T, Struct):
        o = _struct(T, n)
    elif isinstance(T, Array):
        o = _array(T, n)
    else:
        raise TypeError, "malloc for Structs and Arrays only"
    if not isinstance(T, GC_CONTAINER) and not immortal and flavor.startswith('gc'):
        raise TypeError, "gc flavor malloc of a non-GC non-immortal structure"
    solid = immortal or not flavor.startswith('gc') # immortal or non-gc case
    return _ptr(Ptr(T), o, solid)

def flavored_malloc(flavor, T, n=None): # avoids keyword argument usage
    return malloc(T, n, flavor=flavor)
    

def functionptr(TYPE, name, **attrs):
    if not isinstance(TYPE, FuncType):
        raise TypeError, "functionptr() for FuncTypes only"
    try:
        hash(tuple(attrs.items()))
    except TypeError:
        raise TypeError("'%r' must be hashable"%attrs)
    o = _func(TYPE, _name=name, **attrs)
    return _ptr(Ptr(TYPE), o)

def nullptr(T):
    return Ptr(T)._defl()

def opaqueptr(TYPE, name, **attrs):
    if not isinstance(TYPE, OpaqueType):
        raise TypeError, "opaqueptr() for OpaqueTypes only"
    o = _opaque(TYPE, _name=name, **attrs)
    return _ptr(Ptr(TYPE), o, solid=attrs.get('immortal', True))

def pyobjectptr(obj):
    o = _pyobject(obj)
    return _ptr(Ptr(PyObject), o) 

def cast_ptr_to_int(ptr):
    obj = ptr._obj
    while obj._parentstructure():
        obj = obj._parentstructure() 
    return id(obj)


def attachRuntimeTypeInfo(GCSTRUCT, funcptr=None, destrptr=None):
    if not isinstance(GCSTRUCT, GcStruct):
        raise TypeError, "expected a GcStruct: %s" % GCSTRUCT
    GCSTRUCT._attach_runtime_type_info_funcptr(funcptr, destrptr)
    return _ptr(Ptr(RuntimeTypeInfo), GCSTRUCT._runtime_type_info)

def getRuntimeTypeInfo(GCSTRUCT):
    if not isinstance(GCSTRUCT, GcStruct):
        raise TypeError, "expected a GcStruct: %s" % GCSTRUCT
    if GCSTRUCT._runtime_type_info is None:
        raise ValueError, "no attached runtime type info for %s" % GCSTRUCT
    return _ptr(Ptr(RuntimeTypeInfo), GCSTRUCT._runtime_type_info)

def runtime_type_info(p):
    T = typeOf(p)
    if not isinstance(T, Ptr) or not isinstance(T.TO, GcStruct):
        raise TypeError, "runtime_type_info on non-GcStruct pointer: %s" % p
    top_parent = struct = p._obj
    while True:
        parent = top_parent._parentstructure()
        if parent is None:
            break
        top_parent = parent
    result = getRuntimeTypeInfo(top_parent._TYPE)
    static_info = getRuntimeTypeInfo(T.TO)
    query_funcptr = getattr(static_info._obj, 'query_funcptr', None)
    if query_funcptr is not None:
        T = typeOf(query_funcptr).TO.ARGS[0]
        result2 = query_funcptr(cast_pointer(T, p))
        if result != result2:
            raise RuntimeError, ("runtime type-info function for %s:\n"
                                 "        returned: %s,\n"
                                 "should have been: %s" % (p, result2, result))
    return result

def isCompatibleType(TYPE1, TYPE2):
    return TYPE1 == TYPE2

# mark type ADT methods

def typeMethod(func):
    func._type_method = True
    return func
    

