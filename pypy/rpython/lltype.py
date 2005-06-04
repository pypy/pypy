import weakref
import py
from pypy.rpython.rarithmetic import r_uint
from pypy.tool.uid import Hashable
from pypy.tool.tls import tlsobject

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

class frozendict(dict):

    def __hash__(self):
        items = self.items()
        items.sort()
        return hash(tuple(items))
    __hash__ = saferecursive(__hash__, 0)


class LowLevelType(object):
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__
    __eq__ = saferecursive(__eq__, True)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        items = self.__dict__.items()
        items.sort()
        return hash((self.__class__,) + tuple(items))
    __hash__ = saferecursive(__hash__, 0)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return self.__class__.__name__

    def _defl(self, parent=None, parentindex=None):
        raise NotImplementedError

    def _freeze_(self):
        return True

    def _inline_is_varsize(self, last):
        return False


class ContainerType(LowLevelType):
    def _inline_is_varsize(self, last):
        raise TypeError, "%r cannot be inlined in structure" % self


class Struct(ContainerType):
    def __init__(self, name, *fields):
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

    def _inline_is_varsize(self, last):
        if self._arrayfld:
            raise TypeError("cannot inline a var-sized struct "
                            "inside another struct")
        return False

    def __getattr__(self, name):
        try:
            return self._flds[name]
        except KeyError:
            raise AttributeError, 'struct %s has no field %r' % (self._name,
                                                                 name)

    def _str_fields(self):
        return ', '.join(['%s: %s' % (name, self._flds[name])
                          for name in self._names])
    _str_fields = saferecursive(_str_fields, '...')

    def __str__(self):
        return "%s %s { %s }" % (self.__class__.__name__,
                                 self._name, self._str_fields())

    def _defl(self, parent=None, parentindex=None):
        return _struct(self, parent=parent, parentindex=parentindex)

    def _container_example(self):
        if self._arrayfld is None:
            n = None
        else:
            n = 1
        return _struct(self, n)

class GcStruct(Struct):
    pass

class Array(ContainerType):
    __name__ = 'array'
    def __init__(self, *fields):
        self.OF = Struct("<arrayitem>", *fields)
        if self.OF._arrayfld is not None:
            raise TypeError("array cannot contain an inlined array")

    def _inline_is_varsize(self, last):
        if not last:
            raise TypeError("array field must be last")
        return True

    def __str__(self):
        return "%s of { %s }" % (self.__class__.__name__,
                                 self.OF._str_fields(),)

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

    def _container_example(self):
        def ex(*args):
            return self.RESULT._example()
        return _func(self, _callable=ex)

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
    
    _example = _defl


Signed   = Primitive("Signed", 0)
Unsigned = Primitive("Unsigned", r_uint(0))
Float    = Primitive("Float", 0.0)
Char     = Primitive("Char", '\x00')
Bool     = Primitive("Bool", False)
Void     = Primitive("Void", None)


class _PtrType(LowLevelType):
    __name__ = property(lambda self: '%sPtr' % self.TO.__name__)

    def __init__(self, TO, **flags):
        if not isinstance(TO, ContainerType):
            raise TypeError, ("can only point to a Container type, "
                              "not to %s" % (TO,))
        if 'gc' in flags:
            if not isinstance(TO, GC_CONTAINER):
                raise TypeError, ("GcPtr can only point to GcStruct, GcArray or"
                                  " PyObject, not to %s" % (TO,))
        self.TO = TO
        self.flags = frozendict(flags)

    def _str_flags(self):
        flags = self.flags.keys()
        flags.sort()
        result = []
        for flag in flags:
            if self.flags[flag] is not True:
                flag = '%s=%r' % (flag, self.flags[flag])
            result.append(flag)
        return ', '.join(result)

    def _str_flavor(self):
        return 'ptr(%s)' % self._str_flags()

    def __str__(self):
        return '%s to %s' % (self._str_flavor(), self.TO)

    def _defl(self, parent=None, parentindex=None):
        return _ptr(self, None)

    def _example(self):
        o = self.TO._container_example()
        return _ptr(self, o)

    def withflags(self, **flags):
        newflags = self.flags.copy()
        newflags.update(flags)
        return _PtrType(self.TO, **newflags)

def GcPtr(TO, **flags):
    return _PtrType(TO, gc=True, **flags)

def NonGcPtr(TO, **flags):
    return _PtrType(TO, **flags)


# ____________________________________________________________


def typeOf(val):
    if isinstance(val, bool):
        return Bool
    if isinstance(val, r_uint):
        return Unsigned
    if isinstance(val, int):
        return Signed
    if isinstance(val, float):
        return Float
    if isinstance(val, str):
        assert len(val) == 1
        return Char
    if val is None:
        return Void   # maybe
    return val._TYPE

class InvalidCast(TypeError):
    pass

def cast_flags(PTRTYPE, ptr):
    if not isinstance(ptr, _ptr) or not isinstance(PTRTYPE, _PtrType):
        raise TypeError, "can only cast pointers to other pointers"
    CURTYPE = ptr._TYPE
    if CURTYPE.TO != PTRTYPE.TO:
        raise TypeError, "cast_flags only between pointers to the same type"
    # allowed direct casts (for others, you need several casts):
    # * adding one flag
    curflags = CURTYPE.flags
    newflags = PTRTYPE.flags
    if len(curflags) + 1 == len(newflags):
        for key in curflags:
            if key not in newflags or curflags[key] != newflags[key]:
                raise InvalidCast(CURTYPE, PTRTYPE)
    # * removing one flag
    elif len(curflags) - 1 == len(newflags):
        for key in newflags:
            if key not in curflags or curflags[key] != newflags[key]:
                raise InvalidCast(CURTYPE, PTRTYPE)
    # end
    else:
        raise InvalidCast(CURTYPE, PTRTYPE)
    return _ptr(PTRTYPE, ptr._obj)

def cast_parent(PTRTYPE, ptr):
    if not isinstance(ptr, _ptr) or not isinstance(PTRTYPE, _PtrType):
        raise TypeError, "can only cast pointers to other pointers"
    CURTYPE = ptr._TYPE
    if CURTYPE.flags != PTRTYPE.flags:
        raise TypeError("cast_parent() cannot change the flags (%s) to (%s)"
                        % (CURTYPE._str_flags(), PTRTYPE._str_flags()))
    # * converting from TO-structure to a parent TO-structure whose first
    #     field is the original structure
    if (not isinstance(CURTYPE.TO, Struct) or
        not isinstance(PTRTYPE.TO, Struct) or
        len(PTRTYPE.TO._names) == 0 or
        PTRTYPE.TO._flds[PTRTYPE.TO._names[0]] != CURTYPE.TO):
        raise InvalidCast(CURTYPE, PTRTYPE)
    ptr._check()
    parent = ptr._obj._wrparent()
    PARENTTYPE = ptr._obj._wrparent_type
    if getattr(parent, PARENTTYPE._names[0]) is not ptr._obj:
        raise InvalidCast(CURTYPE, PTRTYPE)
    return _ptr(PTRTYPE, parent)


def _TmpPtr(TO):
    return _PtrType(TO, _tmp=True)

def _expose(val, can_have_gc=False):
    """XXX A nice docstring here"""
    T = typeOf(val)
    if isinstance(T, ContainerType):
        assert not isinstance(T, FuncType), "functions cannot be substructures"
        if can_have_gc and isinstance(T, GcStruct):
            val = _ptr(GcPtr(T), val)
        else:
            val = _ptr(_TmpPtr(T), val)
    return val

def parentlink(container):
    parent = container._parentstructure()
    if parent is not None:
        return parent, container._wrparent_index
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

    def __init__(self, TYPE, pointing_to):
        self.__dict__['_TYPE'] = TYPE
        self.__dict__['_T'] = TYPE.TO
        self.__dict__['_obj'] = pointing_to

    def __eq__(self, other):
        if not isinstance(other, _ptr):
            raise TypeError("comparing pointer with %r object" % (
                type(other).__name__,))
        if self._TYPE != other._TYPE:
            raise TypeError("comparing %r and %r" % (self._TYPE, other._TYPE))
        return self._obj is other._obj

    def __ne__(self, other):
        return not (self == other)

    def __nonzero__(self):
        return self._obj is not None

    def _check(self):
        if self._obj is None:
            raise RuntimeError("dereferencing 'NULL' pointer to %r" % (self._T,))
        self._obj._check()

    def __getattr__(self, field_name): # ! can only return basic or ptr !
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                self._check()
                o = getattr(self._obj, field_name)
                can_have_gc = (field_name == self._T._names[0] and
                               'gc' in self._TYPE.flags)
                return _expose(o, can_have_gc)
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    def _setfirst(self, p):
        if isinstance(self._T, Struct) and self._T._names:
            if not isinstance(p, _ptr) or not isinstance(p._obj, _struct):
                raise InvalidCast(typeOf(p), typeOf(self))
            field_name = self._T._names[0]
            T1 = self._T._flds[field_name]
            T2 = typeOf(p._obj)
            if T1 != T2:
                raise InvalidCast(typeOf(p), typeOf(self))
            self._check()
            setattr(self._obj, field_name, p._obj)
            p._obj._wrparent = weakref.ref(self._obj)
            p._obj._wrparent_type = typeOf(self._obj)
            return
        raise TypeError("%r instance has no first field" % (self._T,))

    def __setattr__(self, field_name, val):
        if isinstance(self._T, Struct):
            if field_name in self._T._flds:
                T1 = self._T._flds[field_name]
                T2 = typeOf(val)
                if T1 != T2:
                    raise TypeError("%r instance field %r:\n"
                                    "expects %r\n"
                                    "    got %r" % (self._T, field_name, T1, T2))
                self._check()
                setattr(self._obj, field_name, val)
                return
        raise AttributeError("%r instance has no field %r" % (self._T,
                                                              field_name))

    def __getitem__(self, i): # ! can only return basic or ptr !
        if isinstance(self._T, Array):
            self._check()
            if not (0 <= i < len(self._obj.items)):
                raise IndexError("array index out of bounds")
            o = self._obj.items[i]
            return _expose(o)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __setitem__(self, i, val): # ! not allowed !
        if isinstance(self._T, Array):
            raise TypeError("cannot directly assign to array items")
        raise TypeError("%r instance is not an array" % (self._T,))

    def __len__(self):
        if isinstance(self._T, Array):
            self._check()
            return len(self._obj.items)
        raise TypeError("%r instance is not an array" % (self._T,))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s to %s' % (self._TYPE._str_flavor(), self._obj)

    def __call__(self, *args):
        if isinstance(self._T, FuncType):
            self._check()
            if len(args) != len(self._T.ARGS):
                raise TypeError,"calling %r with wrong argument number: %r" % (self._T, args)
            for a, ARG in zip(args, self._T.ARGS):
                if typeOf(a) != ARG:
                    raise TypeError,"calling %r with wrong argument types: %r" % (self._T, args)
            return self._obj._callable(*args)
        raise TypeError("%r instance is not a function" % (self._T,))
            

class _struct(object):
    _wrparent = None

    def __init__(self, TYPE, n=None, parent=None, parentindex=None):
        self._TYPE = TYPE
        if n is not None and TYPE._arrayfld is None:
            raise TypeError("%r is not variable-sized" % (TYPE,))
        if n is None and TYPE._arrayfld is not None:
            raise TypeError("%r is variable-sized" % (TYPE,))
        for fld, typ in TYPE._flds.items():
            if isinstance(typ, Struct):
                value = _struct(typ, parent=self, parentindex=fld)
            elif fld == TYPE._arrayfld:
                value = _array(typ, n, parent=self, parentindex=fld)
            else:
                value = typ._defl()
            setattr(self, fld, value)
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)
            self._wrparent_index = parentindex

    def _parentstructure(self):
        if self._wrparent is not None:
            parent = self._wrparent()
            if parent is None:
                raise RuntimeError("accessing substructure %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))
            return parent
        return None

    def _check(self):
        parent = self._parentstructure()
        if parent is not None:
            parent._check()

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

class _array(object):
    _wrparent = None

    def __init__(self, TYPE, n, parent=None, parentindex=None):
        if not isinstance(n, int):
            raise TypeError, "array length must be an int"
        if n < 0:
            raise ValueError, "negative array length"
        self._TYPE = TYPE
        self.items = [TYPE.OF._defl(parent=self, parentindex=j)
                      for j in range(n)]
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)
            self._wrparent_index = parentindex

    def _parentstructure(self):
        if self._wrparent is not None:
            parent = self._wrparent()
            if parent is None:
                raise RuntimeError("accessing subarray %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))
            return parent
        return None

    def _check(self):
        parent = self._parentstructure()
        if parent is not None:
            parent._check()

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return 'array [ %s ]' % (', '.join(['{%s}' % item._str_fields()
                                            for item in self.items]),)

class _func(object):
    def __init__(self, TYPE, **attrs):
        self._TYPE = TYPE
        self._name = "?"
        self._callable = None
        self.__dict__.update(attrs)

    def _parentstructure(self):
        return None

    def _check(self):
        if self._callable is None:
            raise RuntimeError,"calling undefined function"

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "func %s" % self._name

class _pyobject(Hashable):
    _TYPE = PyObject

    def _parentstructure(self):
        return None

    def _check(self):
        pass

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "pyobject %s" % (super(_pyobject, self).__str__(),)


def malloc(T, n=None, immortal=False):
    if isinstance(T, Struct):
        o = _struct(T, n)
    elif isinstance(T, Array):
        o = _array(T, n)
    else:
        raise TypeError, "malloc for Structs and Arrays only"
    if immortal:
        T = NonGcPtr(T)
    else:
        T = GcPtr(T)
    return _ptr(T, o)

def functionptr(TYPE, name, **attrs):
    if not isinstance(TYPE, FuncType):
        raise TypeError, "function() for FuncTypes only"
    o = _func(TYPE, _name=name, **attrs)
    return _ptr(NonGcPtr(TYPE), o)

def nullptr(T):
    return _ptr(NonGcPtr(T), None)

def nullgcptr(T):
    return _ptr(GcPtr(T), None)

def pyobjectptr(obj):
    o = _pyobject(obj)
    return _ptr(NonGcPtr(PyObject), o)

def pyobjectgcptr(obj):
    o = _pyobject(obj)
    return _ptr(GcPtr(PyObject), o)
