import weakref
import py
from pypy.rpython.rarithmetic import r_uint

class frozendict(dict):

    def __hash__(self):
        items = self.items()
        items.sort()
        return hash(tuple(items))


class LowLevelType(object):
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__
    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        items = self.__dict__.items()
        items.sort()
        return hash((self.__class__,) + tuple(items))

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return self.__class__.__name__

    def _defl(self, parent=None):
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
        self._name = name
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
 
        # look if we have an inlined variable-sized array as the last field
        if fields:
            for name, typ in fields[:-1]:
                typ._inline_is_varsize(False)
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

    def __str__(self):
        return "Struct %s { %s }" % (self._name, self._str_fields())

    def _defl(self, parent=None):
        return _struct(self, parent=parent)

    def _container_example(self):
        if self._arrayfld is None:
            n = None
        else:
            n = 1
        return _struct(self, n)

class Array(ContainerType):
    def __init__(self, *fields):
        self.OF = Struct("<arrayitem>", *fields)
        if self.OF._arrayfld is not None:
            raise TypeError("array cannot contain an inlined array")

    def _inline_is_varsize(self, last):
        if not last:
            raise TypeError("array field must be last")
        return True

    def __str__(self):
        return "Array of { %s }" % (self.OF._str_fields(),)

    def _container_example(self):
        return _array(self, 1)

class FuncType(ContainerType):
    def __init__(self, args, result):
        for arg in args:
            if isinstance(arg, ContainerType):
                raise TypeError, "function arguments can only be primitives or pointers"
        self.ARGS = tuple(args)
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
    def __str__(self):
        return "PyObject"
PyObject = PyObjectType()

class ForwardReference(ContainerType):
    def become(self, realcontainertype):
        self.__class__ = realcontainertype.__class__
        self.__dict__ = realcontainertype.__dict__


class Primitive(LowLevelType):
    def __init__(self, name, default):
        self._name = name
        self._default = default

    def __str__(self):
        return self._name

    def _defl(self, parent=None):
        return self._default
    
    _example = _defl


Signed   = Primitive("Signed", 0)
Unsigned = Primitive("Unsigned", r_uint(0))
Char     = Primitive("Char", '\x00')
Bool     = Primitive("Bool", False)
Void     = Primitive("Void", None)


class _PtrType(LowLevelType):
    def __init__(self, TO, **flags):
        if not isinstance(TO, ContainerType):
            raise TypeError, ("can only point to a Struct or an Array or a FuncType, "
                              "not to %s" % (TO,))
        self.TO = TO
        self.flags = frozendict(flags)
        if isinstance(TO, FuncType) and 'gc' in self.flags:
            raise TypeError, "function pointers are not gc-able"

    def _str_flags(self):
        flags = self.flags.keys()
        flags.sort()
        result = []
        for flag in flags:
            if self.flags[flag] is not True:
                flag = '%s=%r' % (flag, self.flags[flag])
            result.append(flag)
        return ', '.join(result)

    def __str__(self):
        return 'ptr(%s) to %s' % (self._str_flags(), self.TO)

    def _defl(self, parent=None):
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
        not isinstance(PTRTYPE.TO, Struct)):
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
        if can_have_gc and isinstance(T, Struct):
            val = _ptr(GcPtr(T), val)
        else:
            val = _ptr(_TmpPtr(T), val)
    return val


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

    def _first(self):
        if isinstance(self._T, Struct) and self._T._names:
            return self.__getattr__(self._T._names[0])
        raise AttributeError("%r instance has no first field" % (self._T,))

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
        return '%s to %s' % (self._TYPE.__class__.__name__.lower(), self._obj)

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

    def __init__(self, TYPE, n=None, parent=None):
        self._TYPE = TYPE
        if n is not None and TYPE._arrayfld is None:
            raise TypeError("%r is not variable-sized" % (TYPE,))
        if n is None and TYPE._arrayfld is not None:
            raise TypeError("%r is variable-sized" % (TYPE,))
        for fld, typ in TYPE._flds.items():
            if isinstance(typ, Struct):
                value = _struct(typ, parent=self)
            elif fld == TYPE._arrayfld:
                value = _array(typ, n, parent=self)
            else:
                value = typ._defl()
            setattr(self, fld, value)
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)

    def _check(self):
        if self._wrparent is not None:
            parent = self._wrparent()
            if parent is None:
                raise RuntimeError("accessing substructure %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))
            else:
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

    def __init__(self, TYPE, n, parent=None):
        if not isinstance(n, int):
            raise TypeError, "array length must be an int"
        if n < 0:
            raise ValueError, "negative array length"
        self._TYPE = TYPE
        self.items = [TYPE.OF._defl(parent=self) for j in range(n)]
        if parent is not None:
            self._wrparent_type = typeOf(parent)
            self._wrparent = weakref.ref(parent)

    def _check(self):
        if self._wrparent is not None:
            parent = self._wrparent()
            if parent is None:
                raise RuntimeError("accessing subarray %r,\n"
                                   "but already garbage collected parent %r"
                                   % (self, self._wrparent_type))
            else:
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

    def _check(self):
        if self._callable is None:
            raise RuntimeError,"calling undefined function"

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return "func %s" % self._name

def malloc(T, n=None):
    if isinstance(T, Struct):
        o = _struct(T, n)
    elif isinstance(T, Array):
        o = _array(T, n)
    else:
        raise TypeError, "malloc for Structs and Arrays only"
    return _ptr(GcPtr(T), o)

